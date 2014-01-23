from collections import namedtuple
from copy import copy

import venusian

from tangled.util import fully_qualified_name
from tangled.web.const import ALL_HTTP_METHODS


class config:

    """Decorator for configuring resources methods.

    When used on a resource class, the class level configuration will be
    applied to all methods.

    Example::

        class MyResource:

            @config('text/html', template='my_resource.mako')
            def GET(self):
                pass

    Example of defaults and overrides::

        @config('*/*', status=303, response_attrs={'location': '/'})
        class MyResource:

            @config('*/*', status=302)
            @config('text/html', status=None, response_attrs={})
            def GET(self):
                pass

    """

    callbacks = []  # For tests

    def __init__(self, content_type, **kwargs):
        self.content_type = content_type
        if 'redirect' in kwargs:
            kwargs['status'] = kwargs.pop('redirect')
        if not kwargs:
            raise TypeError('@config requires at least one keyword arg')
        self.kwargs = kwargs

    def __call__(self, wrapped):
        def venusian_callback(scanner, *_):
            app = scanner.app

            # This is here so the app won't start if any of the args
            # passed to @config are invalid. Otherwise, the invalid args
            # wouldn't be detected until a request is made to a resource
            # that was decorated with invalid args.
            # NOTE: We can't check *everything* preemptively here, but
            # we do what we can.
            if isinstance(wrapped, type):
                Config(app, 'GET', self.content_type, **self.kwargs)
            elif wrapped.__name__ in ALL_HTTP_METHODS:
                Config(app, wrapped.__name__, self.content_type, **self.kwargs)

            fq_name = fully_qualified_name(wrapped)
            differentiator = fq_name, self.content_type
            if app.contains(config, differentiator):
                app.get(config, differentiator).update(self.kwargs)
            else:
                app.register(config, self.kwargs, differentiator)
        venusian.attach(wrapped, venusian_callback, category='tangled')
        self.__class__.callbacks.append(venusian_callback)
        return wrapped


_fields = ('methods', 'content_type', 'name', 'default', 'required')
ConfigArg = type('ConfigArg', (namedtuple('ConfigArg', _fields),), {})
Field = type('Field', (ConfigArg,), {})
RepresentationArg = type('RepresentationArg', (ConfigArg,), {})


class Config:

    def __init__(self, app, request_method, content_type, **kwargs):
        self.request_method = request_method
        self.content_type = content_type
        self.representation_args = {}

        all_fields = set()
        all_args = set()

        def set_default_fields(fields):
            if fields:
                for field in fields.values():
                    name = field.name
                    all_fields.add(name)
                    if field.required:
                        if name not in kwargs:
                            raise TypeError
                    else:
                        default = field.default
                        if callable(default):
                            default = default()
                        else:
                            default = copy(default)
                        setattr(self, field.name, default)

        set_default_fields(app.get(Field, (request_method, '*/*')))
        if content_type != '*/*':
            set_default_fields(app.get(Field, (request_method, content_type)))

        def set_default_args(args):
            if args:
                for arg in args.values():
                    name = arg.name
                    all_args.add(name)
                    if arg.required:
                        if name not in kwargs:
                            raise TypeError
                    else:
                        default = arg.default
                        if callable(default):
                            default = default()
                        else:
                            default = copy(default)
                        self.representation_args[name] = default

        set_default_args(app.get(RepresentationArg, (request_method, '*/*')))
        if content_type != '*/*':
            set_default_args(
                app.get(RepresentationArg, (request_method, content_type)))

        for name, value in kwargs.items():
            value = copy(value)
            if name in all_fields:
                setattr(self, name, value)
            elif name in all_args:
                self.representation_args[name] = value
            else:
                raise TypeError(
                    'Unknown @config arg for {} {}: {}'
                    .format(request_method, content_type, name))

    @classmethod
    def for_resource(cls, app, resource, request_method, content_type,
                     resource_method=None):
        """Get :class:`Config` for resource, method, & content type.

        This collects all the relevant config set via ``@config`` and
        combines it with the default config. Default config is set when
        ``@config`` args are added via :meth:`add_config_field` and
        :meth:`add_representation_arg`.

        Returns an info structure populated with class level defaults
        for */* plus method level info for ``content_type``.

        If the resource method name differs from the request method
        name, pass ``resource_method`` so the method level config can be
        found.

        Typically, this wouldn't be used directly; usually
        :meth:`Request.resource_config` would be used to get the
        info for the resource associated with the current request.

        """
        resource_cls = resource.__class__
        resource_method = resource_method or request_method
        resource_method = getattr(resource_cls, resource_method)
        cls_name = fully_qualified_name(resource_cls)
        meth_name = fully_qualified_name(resource_method)
        data = (
            app.get(config, (cls_name, '*/*')),
            app.get(config, (cls_name, content_type)),
            app.get(config, (meth_name, '*/*')),
            app.get(config, (meth_name, content_type)),
        )
        kwargs = {}
        for d in data:
            if d:
                kwargs.update(d)
        return cls(app, request_method, content_type, **kwargs)
