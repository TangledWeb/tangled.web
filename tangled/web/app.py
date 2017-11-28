import configparser
import logging
import logging.config
import pdb
import re

from webob.exc import HTTPInternalServerError

import tangled.decorators
from tangled.converters import as_tuple
from tangled.decorators import cached_property, fire_actions
from tangled.registry import ARegistry, process_registry
from tangled.util import (
    NOT_SET,
    abs_path,
    get_items_with_key_prefix,
    load_object,
)

from . import abcs, representations
from .const import ALL_HTTP_METHODS
from .events import Subscriber, ApplicationCreated
from .exc import DebugHTTPInternalServerError
from .handlers import HandlerWrapper
from .representations import Representation
from .resource.config import Field as ConfigField, RepresentationArg
from .resource.mounted import MountedResourceTree, MountedResource
from .settings import make_app_settings
from .static import LocalDirectory, RemoteDirectory


log = logging.getLogger(__name__)


Registry = process_registry[ARegistry]


class Application(Registry):

    """Application container.

    The application container handles configuration and provides the
    WSGI interface. It is passed to components such as handlers,
    requests, and resources so they can inspect settings, retrieve
    items from the registry, etc...

    **Registry:**

    Speaking of which, the application instance acts as a registry (it's
    a subclass of :class:`tangled.registry.Registry`). This provides
    a means for extensions and application code to set application level
    globals.

    **Settings:**

    ``settings`` can be passed as either a file name pointing to a
    settings file or as a dict.

    File names can be specified as absolute, relative, or asset paths:

        - development.ini
        - /some/where/production.ini
        - some.package:some.ini

    A plain dict can be used when no special handling of settings is
    required. For more control of how settings are parsed (or to
    disable parsing), pass a :class:`.AAppSettings` instance instead
    (typically, but not necessarily, created by calling
    :func:`tangled.web.settings.make_app_settings`).

    Extra settings can be passed as keyword args. These settings will
    override *all* other settings. They will be parsed along with other
    settings.

    NOTE: If ``settings`` is an :class:`.AppSettings` instance,
    extra settings passed here will be ignored; pass them to the
    :class:`.AppSettings` instead.

    **Logging:**

    If settings are loaded from a file and that file (or one of the
    files it extends) contains logging config sections (``formatters``,
    ``handlers``, ``loggers``), that logging configuration will
    automatically be loaded via ``logging.config.fileConfig``.

    """

    def __init__(self, settings, **extra_settings):
        if not isinstance(settings, abcs.AAppSettings):
            settings = make_app_settings(settings, **extra_settings)
        self.settings = settings

        package = settings.get('package')

        self.register(abcs.AMountedResourceTree, MountedResourceTree())

        # Register default representations (content type => repr. type).
        # Includes can override this.
        for obj in vars(representations).values():
            is_representation_type = (
                isinstance(obj, type) and
                issubclass(obj, Representation) and
                obj is not Representation)
            if is_representation_type:
                self.register_representation_type(obj)

        self.add_config_field('*/*', 'quality', None)
        self.add_config_field('*/*', 'type', None)
        self.add_config_field('*/*', 'status', None)
        self.add_config_field('*/*', 'location', None)
        self.add_config_field('*/*', 'response_attrs', dict)

        # Handlers added from settings have precedence over handlers
        # added via includes.
        handlers = self.get_setting('handlers')
        for handler in handlers:
            self.add_handler(handler)

        # Mount static directories and resources from settings before
        # those from includes. It's assumed that only the main
        # application will specify static directories and resources this
        # way.
        for static_args in self.get_setting('static_directories'):
            self.mount_static_directory(**static_args)

        resources_package = self.get_setting('tangled.app.resources.package', package)

        for resource_args in self.get_setting('resources'):
            factory = resource_args['factory']
            if factory.startswith('.'):
                if resources_package is None:
                    raise ValueError(
                        'Package-relative resource factory "{factory}" requires the package '
                        'containing resources to be specified (set either the `package` or '
                        '`tangled.app.resources.package` setting).'
                        .format(factory=factory))
                factory = '{package}{factory}'.format(package=resources_package, factory=factory)
                resource_args['factory'] = factory
            self.mount_resource(**resource_args)

        # Before config is loaded via load_config()
        if self.get_setting('csrf.enabled'):
            self.include('.csrf')

        for include in self.get_setting('includes'):
            self.include(include)

        for where in self.get_setting('load_config'):
            self.load_config(where)

        request_factory = self.get_setting('request_factory')
        self.register(abcs.ARequest, request_factory)
        response_factory = self.get_setting('response_factory')
        self.register(abcs.AResponse, response_factory)

        # TODO: Not sure this belongs here
        self._configure_logging()

        self.name = self.get_setting('name') or 'id={}'.format(id(self))
        process_registry.register(abcs.AApplication, self, self.name)

        for subscriber in self.get_setting('on_created'):
            self.on_created(subscriber)

        if not self.get_setting('tangled.app.defer_created', False):
            self.created()

    def created(self):
        # Force early loading of handlers. This is intended to shake out
        # more errors without needing to issue a request.
        self._handlers

        self.notify_subscribers(ApplicationCreated, self)
        return self

    def on_created(self, func, priority=None, once=True, **args):
        """Add an :class:`~tangled.web.events.ApplicationCreated`
        subscriber.

        Sets ``once`` to ``True`` by default since
        :class:`~tangled.web.events.ApplicationCreated` is only emitted
        once per application.

        This can be used as a decorator in the simple case where no
        args other than ``func`` need to be passed along to
        :meth:`.add_subscriber`.

        """
        self.add_subscriber(ApplicationCreated, func, priority, once, **args)

    def _configure_logging(self):
        file_names = []
        if '__file__' in self.settings:
            file_names.append(self.settings['__file__'])
            file_names.extend(self.settings['__bases__'])
        keys = 'formatters', 'handlers', 'loggers'
        for file_name in file_names:
            parser = configparser.ConfigParser()
            with open(file_name) as fp:
                parser.read_file(fp)
            if all(k in parser for k in keys):
                logging.config.fileConfig(file_name)
                if self.debug:
                    print('Logging config loaded from {}'.format(file_name))
                break
        else:
            if self.debug:
                print('No logging config found')

    ## Settings

    @cached_property
    def debug(self):
        """Wraps ``self.settings['debug'] merely for convenience."""
        return self.settings['debug']

    @cached_property
    def exc_log_message_factory(self):
        return self.get_setting('exc_log_message_factory')

    def get_setting(self, key, default=NOT_SET):
        """Get a setting; return ``default`` *if* one is passed.

        If ``key`` isn't in settings, try prepending ``'tangled.app.'``.

        If the ``key`` isn't present, return the ``default`` if one was
        passed; if a ``default`` wasn't passed, a KeyError will be
        raised.

        """
        if key in self.settings:
            return self.settings[key]
        app_key = 'tangled.app.' + key
        if app_key in self.settings:
            return self.settings[app_key]
        if default is NOT_SET:
            raise KeyError("'{}' not present in settings".format(key))
        return default

    def get_settings(self, settings=None, prefix='tangled.app.', **kwargs):
        """Get settings with names that start with ``prefix``.

        This is a front end for
        :func:`tangled.util.get_items_with_key_prefix` that sets
        defaults for ``settings`` and ``prefix``.

        By default, this will get the settings from ``self.settings``
        that have a ``'tangled.app.'`` prefix.

        Alternate ``settings`` and/or ``prefix`` can be specified.

        """
        if settings is None:
            settings = self.settings
        return get_items_with_key_prefix(settings, prefix, **kwargs)

    ## Handlers

    @cached_property
    def _handlers(self):
        """Set up the handler chain."""
        settings = self.get_settings(prefix='tangled.app.handler.')
        # System handler chain
        handlers = [settings['exc']]
        if self.has_any('static_directory'):
            # Only enable static file handler if there's at least one
            # local static directory registered.
            dirs = self.get_all('static_directory')
            if any(isinstance(d, LocalDirectory) for d in dirs):
                handlers.append(settings['static_files'])
        handlers.append(settings['tweaker'])
        handlers.append(settings['notifier'])
        handlers.append(settings['resource_finder'])
        if self.get_setting('csrf.enabled'):
            handlers.append(settings['csrf'])
        if 'auth' in settings:
            handlers.append(settings['auth'])
        # Handlers added by extensions and applications
        handlers += self.get_all(abcs.AHandler, [])
        if self.get_setting('cors.enabled'):
            handlers.append(settings['cors'])
        # Main handler
        handlers.append(settings['main'])
        # Wrap handlers
        wrapped_handlers = []
        next_handler = None
        for handler in reversed(handlers):
            handler = load_object(handler)
            handler = HandlerWrapper(handler, next_handler)
            wrapped_handlers.append(handler)
            next_handler = handler
        wrapped_handlers.reverse()
        return wrapped_handlers

    @cached_property
    def _first_handler(self):
        return self._handlers[0]

    @cached_property
    def _request_finished_handler(self):
        """Calls finished callbacks in exc handling context."""
        exc_handler = load_object(self.get_setting('handler.exc'))
        handler = load_object('.handlers:request_finished_handler')
        handler = HandlerWrapper(exc_handler, HandlerWrapper(handler, None))
        return handler

    def handle_request(self, request):
        """Send a request through the handler chain."""
        return self._first_handler(self, request)

    ## Configuration methods

    def include(self, obj):
        """Include some other code.

        If a callable is passed, that callable will be called with this
        app instance as its only argument.

        If a module is passed, it must contain a function named
        ``include``, which will be called as described above.

        """
        obj = load_object(obj, 'include')
        return obj(self)

    def load_config(self, where):
        """Load config registered via decorators."""
        where = load_object(where, level=3)
        fire_actions(where, tags='tangled.web', args=(self,))

    def add_handler(self, handler):
        """Add a handler to the handler chain.

        Handlers added via this method are inserted into the system
        handler chain above the main handler. They will be called in the
        order they are added (the last handler added will be called
        directly before the main handler).

        Handlers are typically functions but can be any callable that
        accepts ``app``, ``request``, and ``next_handler`` args.

        Each handler should either call its ``next_handler``, return a
        response object, or raise an exception.

        TODO: Allow ordering?

        """
        self.register(abcs.AHandler, handler, handler)

    def add_helper(self, helper, name=None, static=False, package=None,
                   replace=False):
        """Add a "helper" function.

        ``helper`` can be a string pointing to the helper or the helper
        itself. If it's a string, ``helper`` and ``package`` will be
        passed to :func:`load_object`.

        Helper functions can be methods that take a ``Helpers`` instance
        as their first arg or they can be static methods. The latter is
        useful for adding third party functions as helpers.

        Helper functions can be accessed via ``request.helpers``. The
        advantage of this is that helpers added as method have access to
        the application and the current request.

        """
        helper = load_object(helper, package=package)
        if name is None:
            name = helper.__name__
        if static:
            helper = staticmethod(helper)
        self.register('helper', helper, name, replace=replace)
        if abcs.AHelpers not in self:
            helpers_factory = self.get_setting('helpers_factory')
            self.register(abcs.AHelpers, load_object(helpers_factory))

    def add_subscriber(self, event_type, func, priority=None, once=False,
                       **args):
        """Add a subscriber for the specified event type.

        ``args`` will be passed to ``func`` as keyword args. (Note: this
        functionality is somewhat esoteric and should perhaps be
        removed.)

        You can also use the :class:`~tangled.web.events.subscriber`
        decorator to register subscribers.

        """
        event_type = load_object(event_type)
        func = load_object(func)
        subscriber = Subscriber(event_type, func, priority, once, args)
        self.register(event_type, subscriber, subscriber)

    def add_config_field(self, content_type, name, *args, **kwargs):
        """Add a config field that can be passed via ``@config``.

        This allows extensions to add additional keyword args for
        ``@config``. These args will be accessible as attributes of
        the :class:`.resource.config.Config` object returned by
        ``request.resource_config``.

        These fields can serve any purpose. For example, a
        ``permission`` field could be added, which would be accessible
        as ``request.resource_config.permission``. This could be checked
        in an auth handler to verify the user has the specified
        permission.

        See :meth:`_add_config_arg` for more detail.

        """
        if name == 'representation_args':
            raise ValueError('{} is a reserved Config field name'.format(name))
        self._add_config_arg(ConfigField, content_type, name, *args, **kwargs)

    def add_representation_arg(self, *args, **kwargs):
        """Add a representation arg that can be specified via @config.

        This allows extensions to add additional keyword args for
        ``@config``. These args will be passed as keyword args to the
        representation type that is used for the request.

        These args are accessible via the ``representation_args`` dict
        of the :class:`.resource.config.Config` object returned by
        ``request.resource_config`` (but generally would not be accessed
        directly).

        See :meth:`_add_config_arg` for more detail.

        """
        self._add_config_arg(RepresentationArg, *args, **kwargs)

    def _add_config_arg(self, type_, content_type, name, default=None,
                        required=False, methods=ALL_HTTP_METHODS):
        """Add an arg that can be passed to ``@config``.

        .. note:: This shouldn't be called directly. It's used by both
            :meth:`add_config_field` and :meth:`add_representation_arg`
            because they work in exactly the same way.

        ``name`` is the name of the arg as it would be passed to
        ``@config`` as a keyword arg.

        If a ``default`` is specified, it can be a callable or any other
        type of object. If it's a callable, it will be used as a factory
        for generating the default. If it's any other type of object, it
        will be used as is.

        If the arg is ``required``, then it *must* be passed via
        ``@config``.

        A list of ``methods`` can be passed to constrain which HTTP
        methods the arg can be used on. By default, all methods are
        allowed. ``methods`` can be specified as a string like ``'GET'``
        or ``'GET,POST'`` or as a list of methods like
        ``('GET', 'POST')``.

        """
        if methods == '*':
            methods = ALL_HTTP_METHODS
        methods = as_tuple(methods, sep=',')
        arg = type_(methods, content_type, name, default, required)
        for method in methods:
            differentiator = (method, content_type)
            if not self.contains(type_, differentiator):
                self.register(type_, Registry(), differentiator)
            registry = self.get(type_, differentiator)
            registry.register(type_, arg, name)

    def mount_resource(self, name, factory, path, methods=(), method_name=None,
                       add_slash=False, _level=3):
        """Mount a resource at the specified path.

        Basic example::

            app.mount_resource('home', 'mypackage.resources:Home', '/')

        Specifying URL vars::

            app.mount_resource(
                'user', 'mypackage.resources:User', '/user/<id>')

        A unique ``name`` for the mounted resource must be specified.
        This can be *any* string. It's used when generating resource
        URLs via :meth:`.request.Request.resource_url`.

        A ``factory`` must also be specified. This can be any class or
        function that produces objects that implement the resource
        interface (typically a subclass of
        :class:`.resource.resource.Resource`). The factory may be passed
        as a string with the following format:
        ``package.module:factory``.

        The ``path`` is an application relative path that may or may not
        include URL vars.

        A list of HTTP ``methods`` can be passed to constrain which
        methods the resource will respond to. By default, it's assumed
        that a resource will respond to all methods. Note however that
        when subclassing :class:`.resource.resource.Resource`,
        unimplemented methods will return a ``405 Method Not Allowed``
        response, so it's often unnecessary to specify the list of
        allowed methods here; this is mainly useful if you want to
        mount different resources at the same path for different
        methods.

        If ``path`` ends with a slash or ``add_slash`` is True, requests
        to ``path`` without a trailing slash will be redirected to the
        ``path`` with a slash appended.

        About URL vars:

        The format of a URL var is ``<(converter)identifier:regex>``.
        Angle brackets delimit URL vars. Only the ``identifier`` is
        required; it can be any valid Python identifier.

        If a ``converter`` is specified, it can be a built-in name,
        the name of a converter in :mod:`tangled.util.converters`, or
        a ``package.module:callable`` path that points to a callable
        that accepts a single argument. URL vars found in a request path
        will be converted automatically.

        The ``regex`` can be *almost* any regular expression. The
        exception is that ``<`` and ``>`` can't be used. In practice,
        this means that named groups (``(?P<name>regex)``) can't be used
        (which would be pointless anyway), nor can "look behinds".

        **Mounting Subresources**

        Subresources can be mounted like this::

            parent = app.mount_resource('parent', factory, '/parent')
            parent.mount('child', 'child')

        or like this::

            with app.mount_resource('parent', factory, '/parent') as parent:
                parent.mount('child', 'child')

        In either case, the subresource's ``name`` will be prepended
        with its parent's name plus a slash, and its ``path`` will be
        prepended with its parent's path plus a slash. If no ``factory``
        is specified, the parent's factory will be used. ``methods``
        will be propagated as well. ``method_name`` and ``add_slash``
        are *not* propagated.

        In the examples above, the child's name would be
        ``parent/child`` and its path would be ``/parent/child``.

        """
        mounted_resource = MountedResource(
            name,
            load_object(factory, level=_level),
            path,
            methods=methods,
            method_name=method_name,
            add_slash=add_slash)
        self.register(
            abcs.AMountedResource, mounted_resource, mounted_resource.name)
        tree = self.get_required(abcs.AMountedResourceTree)
        tree.add(mounted_resource)
        return SubResourceMounter(self, mounted_resource)

    def register_representation_type(self, representation_type, replace=False):
        """Register a content type.

        This does a few things:

        - Makes the representation type accessible via its key
        - Makes the representation type accessible via its content type
        - Registers the representation's content type

        """
        representation_type = load_object(representation_type)
        key = representation_type.key
        content_type = representation_type.content_type
        quality = representation_type.quality
        self.register(
            Representation, representation_type, key, replace=replace)
        self.register(
            Representation, representation_type, content_type, replace=replace)
        self.register(
            'content_type', (content_type, quality), content_type,
            replace=replace)

    def add_request_attribute(self, attr, name=None, decorator=None,
                              reify=False):
        """Add dynamic attribute to requests.

        This is mainly intended so that extensions can easily add
        request methods and properties.

        Functions can already be decorated, or a ``decorator`` can be
        specified. If ``reify`` is ``True``, the function will be
        decorated with :func:`tangled.decorators.cached_property`. If a
        ``decorator`` is passed and ``reify`` is ``True``,
        ``cached_property`` will be applied as the outermost decorator.

        """
        if not name:
            if hasattr(attr, '__name__'):
                name = attr.__name__
            elif isinstance(attr, property):
                name = attr.fget.__name__
        if not name:
            raise ValueError(
                'attribute of type {} requires a name'.format(attr.__class__))
        if callable(attr):
            if decorator:
                attr = decorator(attr)
            if reify:
                attr = tangled.decorators.cached_property(attr)
        elif decorator or reify:
            raise ValueError("can't decorate a non-callable attribute")
        self.register('dynamic_request_attr', attr, name)

    # Static directories

    def mount_static_directory(self, prefix, directory, remote=False,
                               index_page=None):
        """Mount a local or remote static directory.

        ``prefix`` is an alias referring to ``directory``.

        If ``directory`` is just a path, it should be a local directory.
        Requests to ``/{prefix}/{path}`` will look in this directory for
        the file indicated by ``path``.

        If ``directory`` refers to a remote location (i.e., it starts
        with ``http://`` or ``https://``), URLs generated via
        ``reqeust.static_url`` and ``request.static_path`` will point
        to the remote directory.

        ``remote`` can also be specified explicitly. In this context,
        "remote" means not served by the application itself. E.g., you
        might be mapping an alias in Nginx to a local directory.

        .. note:: It's best to always use
                  :meth:`tangled.web.request.Request.static_url`
                  :meth:`tangled.web.request.Request.static_path`
                  to generate static URLs.

        """
        prefix = tuple(prefix.strip('/').split('/'))
        if remote or re.match(r'https?://', directory):
            directory = RemoteDirectory(directory)
        else:
            directory = abs_path(directory)
            directory = LocalDirectory(directory, index_page=index_page)
        self.register('static_directory', directory, prefix)

    def _find_static_directory(self, path):
        """Find static directory for ``path``.

        This attempts to find a registered static directory
        corresponding to ``path``. If there is such a directory, the
        prefix and the remaining segments are both returned as a tuple
        of segments; if there isn't, ``(None, None)`` is returned.

        E.g., for the path /static/images/icon.png, the following
        tuple of tuples will be returned (assuming a static directory
        was mounted with the prefix 'static')::

            (('static'), ('images', 'icon.png'))

        The prefix tuple can be used to find the registered static
        directory::

            app.get('static_directory', prefix)

        The prefix and remaining segments can be used to generate
        URLs.

        """
        if self.has_any('static_directory'):
            prefix = ()
            segments = tuple(path.lstrip('/').split('/'))
            for segment in segments:
                prefix += (segment,)
                if self.contains('static_directory', prefix):
                    return prefix, segments[len(prefix):]
        return None, None

    # Non-configuration methods

    def notify_subscribers(self, event_type, *event_args, **event_kwargs):
        """Call subscribers registered for ``event_type``."""
        subscribers = self.get_all(event_type, default=())
        if subscribers:
            subscribers = sorted(subscribers, key=Subscriber.sorter)
            event = event_type(*event_args, **event_kwargs)
            for subscriber in subscribers:
                subscriber.func(event, **subscriber.args)
                if subscriber.once:
                    self.remove(event_type, subscriber)

    # Request

    def make_request(self, environ, **kwargs):
        """Make a request using the registered request factory."""
        factory = self.get(abcs.ARequest)
        request = factory(environ, self, **kwargs)
        self._set_request_attributes(request)
        return request

    def make_blank_request(self, *args, **kwargs):
        """Make a blank request using the registered request factory."""
        factory = self.get(abcs.ARequest)
        request = factory.blank(*args, app=self, **kwargs)
        self._set_request_attributes(request)
        return request

    def _set_request_attributes(self, request):
        attrs = self.get_all('dynamic_request_attr', as_dict=True)
        if attrs:
            base = request.__class__
            request.__class__ = type(base.__name__, (base,), attrs)

    # WSGI Interface

    def log_exc(self, request, exc, logger=None):
        message = self.exc_log_message_factory(self, request, exc)
        if logger is None:
            logger = logging.getLogger('exc')
        exc_info = exc.__class__, exc, exc.__traceback__
        logger.error(message, exc_info=exc_info)

    def __call__(self, environ, start_response):
        request = None
        response = None  # Signal to callbacks that request failed hard
        try:
            request = self.make_request(environ)
            try:
                response = self.handle_request(request)
            finally:
                request.response = response
                response = self._request_finished_handler(self, request)
            return response(request.environ, start_response)
        except Exception as exc:
            error_message = self.exc_log_message_factory(self, request, exc)
            if self.debug:
                if self.settings.get('debug.pdb', False):
                    pdb.post_mortem(exc.__traceback__)
                response = DebugHTTPInternalServerError(error_message)
            else:
                # Attempt to ensure this exception is logged (i.e., if
                # the exc logger is broken for some reason).
                exc_info = exc.__class__, exc, exc.__traceback__
                log.critical(error_message, exc_info=exc_info)
                response = HTTPInternalServerError()
            try:
                self.log_exc(request, exc)
            finally:
                return response(environ, start_response)

    def __repr__(self):
        return '<Tangled Application {}>'.format(self.name)


class SubResourceMounter:

    def __init__(self, app, parent):
        self.app = app
        self.parent = parent

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_traceback):
        return False

    def mount(self, name, path, factory=None, methods=None, method_name=None,
              add_slash=False):
        name = '/'.join((self.parent.name, name))
        path = '/'.join((self.parent.path, path.lstrip('/')))
        factory = factory if factory is not None else self.parent.factory
        methods = methods if methods is not None else self.parent.methods
        return self.app.mount_resource(
            name, factory, path, methods, method_name, add_slash, _level=4)
