from collections import namedtuple
from copy import deepcopy
from itertools import chain

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
        return wrapped


_fields = ('methods', 'content_type', 'name', 'default', 'required')
ConfigArg = type('ConfigArg', (namedtuple('ConfigArg', _fields),), {})
Field = type('Field', (ConfigArg,), {})
RepresentationArg = type('RepresentationArg', (ConfigArg,), {})


class Config:

    def __init__(self, app, request_method, content_type, **kwargs):
        self.__dict__['request_method'] = request_method
        self.__dict__['content_type'] = content_type
        self.__dict__['representation_args'] = {}

        def _get_args(arg_type):
            all_items = []
            items = app.get(arg_type, (request_method, '*/*'))
            if items:
                all_items.extend(items.values())
            if content_type != '*/*':
                items = app.get(arg_type, (request_method, content_type))
                if items:
                    all_items.extend(items.values())
            return all_items

        _fields = _get_args(Field)
        _args = _get_args(RepresentationArg)

        self._field_names = set(f.name for f in _fields)
        self._arg_names = set(a.name for a in _args)

        kwargs = deepcopy(kwargs)

        for config_arg in chain(_fields, _args):
            name = config_arg.name
            if config_arg.required and name not in kwargs:
                raise TypeError('Missing resource config arg: {}'.format(name))
            else:
                default = config_arg.default
                default = default() if callable(default) else deepcopy(default)
                setattr(self, name, default)

        for name, value in kwargs.items():
            setattr(self, name, value)

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
        data = [app.get(config, (cls_name, '*/*'))]
        if content_type != '*/*':
            data.append(app.get(config, (cls_name, content_type)))
        data.append(app.get(config, (meth_name, '*/*')))
        if content_type != '*/*':
            data.append(app.get(config, (meth_name, content_type)))
        kwargs = {}
        for d in data:
            if d:
                kwargs.update(d)
        return cls(app, request_method, content_type, **kwargs)

    def __setattr__(self, name, value):
        if name.startswith('_') or name in self._field_names:
            super().__setattr__(name, value)
        elif name in self._arg_names:
            self.representation_args[name] = value
        else:
            raise TypeError(
                "can't set {} on {}".format(name, self.__class__))
