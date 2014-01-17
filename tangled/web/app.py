import collections
import configparser
import copy
import logging
import logging.config
import os
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
    fully_qualified_name,
    get_items_with_key_prefix,
    load_object,
)

from . import abcs, representations
from .events import Subscriber, ApplicationCreated
from .exc import ConfigurationError, DebugHTTPInternalServerError
from .handlers import HandlerWrapper
from .representations import Representation
from .resource import MountedResource
from .settings import parse_settings, parse_settings_file


log = logging.getLogger(__name__)


Registry = process_registry[ARegistry]


class Application(Registry):

    """Application container.

    The application container handles configuration and provides the
    WSGI interface.

    The application instance also acts as a registry. This provides
    a means for extensions and application code to set application level
    globals.

    """

    def __init__(self, settings, parse=False):
        super().__init__()  # Initialize as registry

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

        self.add_representation_info_field('*/*', 'type', None)
        self.add_representation_info_field('*/*', 'status', None)
        self.add_representation_info_field('*/*', 'location', None)
        self.add_representation_info_field('*/*', 'response_attrs', {})

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

    def add_representation_info_field(self, content_type, name, *args,
                                      **kwargs):
        if name == 'representation_args':
            raise ValueError('{} is a reserved name'.format(name))
        key = 'representation_info_field'
        self._add_representation_meta(key, content_type, name, *args, **kwargs)

    def add_representation_arg(self, *args, **kwargs):
        key = 'representation_arg'
        self._add_representation_meta(key, *args, **kwargs)

    def _add_representation_meta(self, key, content_type, name,
                                 default=NOT_SET, required=False,
                                 methods='*'):
        if required:
            if default is not NOT_SET:
                raise ValueError("can't set default for required arg")

        methods = as_tuple(methods, sep=',')

        for method in methods:
            _key = [key, (method, content_type)]
            if _key not in self:
                self[_key] = {}
            if name in self[_key]:
                raise ConfigurationError(
                    '{} {} already added for {} {}'
                    .format(key, name, method, content_type))
            self[_key][name] = default

    def mount_resource(self, *args, **kwargs):
        """Mount a resource at the specified path."""
        mounted_resource = MountedResource(*args, **kwargs)
        self.register(
            abcs.AMountedResource, mounted_resource, mounted_resource.name)

    def register_content_type(self, content_type, representation_type,
                              replace=False):
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
        if directory.startswith('http://') or directory.startswith('https://'):
            directory = directory
        else:
            prefix = tuple(prefix.strip('/').split('/'))
            directory = abs_path(directory)
            directory = DirectoryApp(directory, index_page=index_page)
        self.register('static_directory', directory, prefix)

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

    def get_default_representation_info(self, method, content_type):
        """Get default representation info.

        This is the default info that is set by calls to
        :meth:`add_representation_arg` and
        :meth:`add_representation_info_field`.

        """
        def _copy(key):
            dict_ = {}
            dict_.update(self.get(key, ('*', '*/*'), {}))
            dict_.update(self.get(key, ('*', content_type), {}))
            if method != '*':
                dict_.update(self.get(key, (method, '*/*'), {}))
                dict_.update(self.get(key, (method, content_type), {}))
            for k, v in dict_.items():
                dict_[k] = copy.copy(v)
            return dict_

        fields = _copy('representation_info_field')
        fields['representation_args'] = _copy('representation_arg')

        info_type = collections.namedtuple('RepresentationInfo', fields)
        info = info_type(**fields)
        return info

    def get_representation_info(self, resource, method, content_type):
        """Get repr. info for resource, method, and content type.

        This combines the default info from
        :meth:`get_default_representation_info with the info set via
        ``@config``.

        Returns an info structure populated with class level defaults
        for */* and ``content_type`` plus method level info for */* and
        ``content_type``.

        Typically, this wouldn't be used directly; usually
        :meth:`Request.representation_info` would be used to get the
        info for the resource associated with the current request.

        """
        resource_cls = resource.__class__
        resource_method = getattr(resource_cls, method)

        cls_name = fully_qualified_name(resource_cls)
        meth_name = fully_qualified_name(resource_method)

        default_info = self.get_default_representation_info(
            method, content_type)

        field_names = set(default_info._fields)

        fields = {}
        for k in field_names:
            v = getattr(default_info, k)
            if v is not NOT_SET:
                fields[k] = v

        fields['representation_args'] = args = {}
        default_args = default_info.representation_args
        if default_args:
            for k, v in default_args.items():
                if v is not NOT_SET:
                    args[k] = v

        for data in (data for data in (
            self.get('representation_info', (cls_name, '*/*')),
            self.get('representation_info', (cls_name, content_type)),
            self.get('representation_info', (meth_name, '*/*')),
            self.get('representation_info', (meth_name, content_type)),
        ) if data):
            for name, value in data.items():
                if name in field_names:
                    fields[name] = value
                elif name in default_args:
                    args[name] = value

        info = default_info.__class__(**fields)
        return info

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
