import venusian

from tangled.util import NOT_SET, fully_qualified_name


class config:

    """Decorator for configuring resources.

    Example::

        class MyResource:

            @config('text/html', template_name='my_resource.mako')
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
            self._validate_args(app, wrapped)
            fq_name = fully_qualified_name(wrapped)
            key = 'representation_info'
            differentiator = fq_name, self.content_type
            if [key, differentiator] in app:
                app.get(key, differentiator).update(self.kwargs)
            else:
                app.register(key, self.kwargs, differentiator)
        venusian.attach(wrapped, venusian_callback, category='tangled')
        self.__class__.callbacks.append(venusian_callback)
        return wrapped

    def _validate_args(self, app, wrapped):
        # This is here so the app won't start if any of the args passed
        # to @config are invalid. Otherwise, the invalid args
        # wouldn't be detected until a request is made to a resource
        # that was decorated with invalid args.
        method = '*' if isinstance(wrapped, type) else wrapped.__name__
        info = app.get_default_representation_info(method, self.content_type)
        field_names = set(info._fields)
        for k in self.kwargs:
            if not (k in field_names or k in info.representation_args):
                raise TypeError(
                    'Unknown @config arg for {}: {}'
                    .format(self.content_type, k))
        for k in field_names:
            if getattr(info, k) is NOT_SET and k not in self.kwargs:
                raise TypeError(
                    'Missing required @config arg for {}: {}'
                    .format(self.content_type, k))
        for k, v in info.representation_args.items():
            if v is NOT_SET and k not in self.kwargs:
                raise TypeError(
                    'Missing required @config arg for {}: {}'
                    .format(self.content_type, k))
