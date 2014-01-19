import configparser
import logging
import logging.config
import pdb
import traceback

import venusian

from webob.exc import HTTPInternalServerError
from webob.static import DirectoryApp

import tangled.decorators
from tangled.converters import as_tuple
from tangled.decorators import reify
from tangled.registry import ARegistry, process_registry
from tangled.util import (
    NOT_SET,
    abs_path,
    get_items_with_key_prefix,
    load_object,
)

from . import abcs, representations
from .events import Subscriber, ApplicationCreated
from .exc import DebugHTTPInternalServerError
from .handlers import HandlerWrapper
from .representations import Representation
from .resource.config import Field as ConfigField, RepresentationArg
from .resource.mounted import MountedResource
from .settings import parse_settings, parse_settings_file


log = logging.getLogger(__name__)


# TODO: Move this
ALL_HTTP_METHODS = (
    'CONNECT', 'DELETE', 'GET', 'HEAD', 'POST', 'PUT', 'OPTIONS', 'TRACE')


Registry = process_registry[ARegistry]


class Application(Registry):

    """Application container.

    The application container handles configuration and provides the
    WSGI interface. It is passed to components such as handlers,
    requests, and resources so they can inspect settings, retrieve
    items from the registry, etc...

    Speaking of which, the application instance acts as a registry (it's
    a subclass of :class:`tangled.registry.Registry`). This provides
    a means for extensions and application code to set application level
    globals.

    If settings are loaded from a config file and that config file (or
    one of the config files it extends) contains logging config sections
    (``formatters``, ``handlers``, ``loggers``), that logging
    configuration will automatically be loaded via
    ``logging.config.fileConfig``.

    """

    def __init__(self, settings, parse=False):
        if parse:
            settings = self.parse_settings(settings)
        default_settings = self.parse_settings_file(
            'tangled.web:defaults.ini', meta_settings=False)
        self.settings = default_settings
        self.settings.update(settings)

        # Register default representations (content type => repr. type).
        # Includes can override this.
        for obj in vars(representations).values():
            is_representation_type = (
                isinstance(obj, type) and
                issubclass(obj, Representation) and
                obj is not Representation)
            if is_representation_type:
                self.register_content_type(obj.content_type, obj)

        self.add_config_field('*/*', 'type', None)
        self.add_config_field('*/*', 'status', None)
        self.add_config_field('*/*', 'location', None)
        self.add_config_field('*/*', 'response_attrs', dict)

        # Handlers added from includes have precedence over handlers
        # listed in settings.
        handlers = self.get_setting('handlers')
        for handler in handlers:
            self.add_handler(handler)

        # Before scan
        if self.get_setting('csrf.enabled'):
            self.include('.csrf')

        for include in self.get_setting('includes'):
            self.include(include)

        request_factory = self.get_setting('request_factory')
        self.register(abcs.ARequest, request_factory)
        response_factory = self.get_setting('response_factory')
        self.register(abcs.AResponse, response_factory)

        # TODO: Not sure this belongs here
        self._configure_logging()

        name = self.get_setting('name') or id(self)
        process_registry.register(abcs.AApplication, self, name)

        for subscriber in self.get_setting('on_created'):
            self.on_created(subscriber)

        self.notify_subscribers(ApplicationCreated, self)

    def on_created(self, func, priority=None, once=True, **args):
        """Add an :class:`ApplicationCreated` subscriber.

        Sets ``once`` to ``True`` by default since
        ``ApplicationCreated`` is only emitted once per application.

        This can be used as a decorator in the simple case where no
        args other than ``func`` need to be passed along to
        :meth:`add_subscriber`.

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

    @reify
    def debug(self):
        """Wraps ``self.settings['debug'] merely for convenience."""
        return self.settings['debug']

    parse_settings = staticmethod(parse_settings)
    parse_settings_file = staticmethod(parse_settings_file)

    def get_setting(self, key, default=NOT_SET):
        """Get setting; return ``default`` *if* one is passed.

        If ``key`` isn't in settings, try prepending 'tangled.app.'.

        If the ``key`` isn't present, return the ``default`` if one was
        passed; if a ``default`` isn't passed, a KeyError will be
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

        This is front end for :func:`get_items_with_key_prefix` that
        sets defaults for ``settings`` and ``prefix``.

        By default, this will get the settings from ``self.settings``
        that have a 'tangled.app.' prefix.

        Alternate ``settings`` and/or ``prefix`` can be specified.

        """
        if settings is None:
            settings = self.settings
        return get_items_with_key_prefix(settings, prefix, **kwargs)

    ## Handlers

    @reify
    def _handlers(self):
        """Set up the handler chain."""
        settings = self.get_settings(prefix='tangled.app.handler.')
        # System handler chain
        handlers = [settings['exc']]
        if self.has_any('static_directory'):
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

    @reify
    def _first_handler(self):
        return self._handlers[0]

    @reify
    def _request_finished_handler(self):
        """Calls finished callbacks in exc handling context."""
        exc_handler = load_object(self.get_setting('handler.exc'))
        handler = load_object('.handlers:request_finished_handler')
        handler = HandlerWrapper(exc_handler, HandlerWrapper(handler, None))
        return handler

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

    def scan(self, where):
        """Scan the indicated package or module."""
        where = load_object(where, level=3)
        scanner = venusian.Scanner(app=self)
        scanner.scan(where, categories=('tangled',))

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
        as their first args or they can be static methods. The latter is
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

        Creates and registers an instance of :class:`Subscriber`.

        ``args`` will be passed to ``func`` as keyword args. (Note: this
        functionality is somewhat esoteric and should perhaps be
        removed.)

        """
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
        allowed.

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

    def mount_resource(self, *args, **kwargs):
        """Mount a resource at the specified path."""
        mounted_resource = MountedResource(*args, **kwargs)
        self.register(
            abcs.AMountedResource, mounted_resource, mounted_resource.name)

    def register_content_type(self, content_type, representation_type, replace=False):
        """Register a content type.

        This does a few things. First, it registers the ``content_type``
        as being available. Second, it makes the ``representation_type``
        the preferred representation type for the content type. Third,
        it makes the representation type accessible via its ``key`` (and
        it arguably should *not* do this last bit here).

        """
        representation_type = load_object(representation_type)
        key = representation_type.key
        self.register(
            'content_type', content_type, content_type, replace=replace)
        self.register(content_type, representation_type, replace=replace)
        self.register(
            'representation_lookup', representation_type, representation_type,
            replace=replace)
        self.register(
            'representation_lookup', representation_type, key,
            replace=replace)

    def add_request_attribute(self, attr, name=None, decorator=None,
                              reify=False):
        """Add dynamic attribute to requests.

        This is mainly intended so that extensions can easily add
        request methods and properties.

        Functions can already be decorated, or a ``decorator`` can be
        specified. If ``reify`` is ``True``, the function will be
        decorated with :func:`tangled.decorators.reify`. If a
        ``decorator`` is passed and ``reify`` is ``True``, ``reify``
        will be applied as the outermost decorator.

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
                attr = tangled.decorators.reify(attr)
        elif decorator or reify:
            raise ValueError("can't decorate a non-callable attribute")
        self.register('dynamic_request_attr', attr, name)

    # Static directories

    def mount_static_directory(self, prefix, directory, index_page=None):
        """Mount a local or remote static directory.

        ``prefix`` is an alias referring to ``directory``.

        If ``directory`` is just a path, it should be a local directory.
        Requests to ``/{prefix}/{path}`` will look in this directory for
        the file indicated by ``path``.

        If ``directory`` refers to a remote location (i.e., it starts
        with ``http://`` or ``https://``), URLs generated via
        ``reqeust.static_url`` and ``request.static_path`` will point
        to the remote directory.

        .. note:: It's best to always use
                  :meth:`tangled.web.request.Request.static_url`
                  :meth:`tangled.web.request.Request.static_path`
                  to generate static URLs.

        """
        if directory.startswith('http://') or directory.startswith('https://'):
            directory = directory
        else:
            prefix = tuple(prefix.strip('/').split('/'))
            directory = abs_path(directory)
            directory = DirectoryApp(directory, index_page=index_page)
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

    @staticmethod
    def log_exc(request, exc, logger=None):
        message = ''.join(
            traceback.format_exception(exc.__class__, exc, exc.__traceback__))
        if logger is None:
            logger = logging.getLogger('exc')
        logger.error(message)

    def __call__(self, environ, start_response):
        request = None
        response = None  # Signal to callbacks that request failed hard
        try:
            request = self.make_request(environ)
            try:
                response = self._first_handler(self, request)
            finally:
                request.response = response
                response = self._request_finished_handler(self, request)
            return response(request.environ, start_response)
        except Exception as exc:
            error_message = traceback.format_exc()
            if self.debug:
                if self.settings.get('debug.pdb', False):
                    pdb.post_mortem(exc.__traceback__)
                response = DebugHTTPInternalServerError(error_message)
            else:
                # Attempt to ensure this exception is logged (i.e., if
                # the exc logger is broken for some reason).
                log.critical(error_message)
                response = HTTPInternalServerError()
            try:
                self.log_exc(request, exc)
            finally:
                return response(environ, start_response)
