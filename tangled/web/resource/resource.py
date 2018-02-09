from inspect import ismethod, signature, Parameter
from urllib.parse import unquote, unquote_plus

from webob.exc import HTTPMethodNotAllowed

from tangled.decorators import cached_property
from tangled.util import as_bool
from tangled.web import csrf
from tangled.web.response import Response

from .exc import BindError


class Resource:

    """Base resource class.

    Usually, you will want to subclass :class:`Resource` when creating
    your own resources. Doing so will ensure your resources are properly
    initialized.

    Subclasses will automatically return a ``405 Method Not Allowed``
    response for unimplemented methods.

    Subclasses also have :meth:`.url` and :meth:`.path` methods that
    generate URLs and paths to the "current resource". E.g., in a
    template, you can do ``resource.path()`` to generate the
    application-relative path to the current resource. You can also pass
    in query parameters and alternate URL vars to generate URLs and
    paths based on the current resource.

    """

    empty = Parameter.empty

    def __init__(self, app, request, name=None):
        self.app = app
        self.request = request
        self.name = name

    def bind(self, request, method):
        """Bind the request to this resource.

        Inspired by :meth:`inspect.Signature.bind` in the standard library,
        this extracts URL vars, GET parameters, POST data, and JSON data and
        "binds" them to the request's resource method.

        Sets ``request.resource_args``, which has ``args`` and ``kwargs``
        attributes corresponding the resource method's positional and
        keyword arguments (it's an instance of
        :class:`inspect.BoundArguments`).

        """
        def add_args_from(data, source, *, exclude=(), decoder=None):
            added_args = {}
            for n, v in data.items():
                if n in exclude:
                    continue
                if n in args:
                    messages.append('{name} duplicated in {source} args'.format_map(locals()))
                else:
                    if decoder:
                        v = decoder(v)
                    args[n] = v

        args = {}
        messages = []

        add_args_from(request.urlvars, 'URL', decoder=unquote)
        add_args_from(request.GET, 'GET', decoder=unquote_plus)
        if request.content_type == 'application/json':
            add_args_from(request.json, 'JSON')
        add_args_from(
            request.POST, 'POST', exclude=[csrf.get_token(request)],
            decoder=unquote)

        if messages:
            raise BindError(self, request, method, ', '.join(messages))

        method = getattr(self, method)
        method_signature = signature(method)
        parameters = method_signature.parameters

        try:
            bound_args = method_signature.bind(**args)
        except TypeError as exc:
            raise BindError(self, request, method, exc)

        for name, value in bound_args.arguments.items():
            parameter = parameters[name]
            kind = parameter.annotation
            if kind is parameter.empty:
                default = parameter.default
                if default is parameter.empty or default is None:
                    kind = str
                else:
                    kind = default.__class__
            if kind is bool:
                kind = as_bool
            try:
                value = kind(value)
            except ValueError as exc:
                raise BindError(self, request, method, exc)
            bound_args.arguments[name] = value

        return bound_args

    def url(self, urlvars, **kwargs):
        """Generate a fully qualified URL for this resource.

        You can pass ``urlvars``, ``query``, and/or ``fragment`` to
        generate a URL based on this resource.

        """
        return self.request.resource_url(self, urlvars, **kwargs)

    def path(self, urlvars, **kwargs):
        """Generate an application-relative URL path for this resource.

        You can pass ``urlvars``, ``query``, and/or ``fragment`` to
        generate a path based on this resource.

        """
        return self.request.resource_path(self, urlvars, **kwargs)

    def allows_method(self, method):
        method = getattr(self, method, None)
        return ismethod(method) and method.__func__ is not self.__class__.NOT_ALLOWED

    @cached_property
    def allowed_methods(self):
        candidates = (
            name for name in dir(self)
            if not name.startswith('_') and name.isupper() and ismethod(getattr(self, name))
        )
        allowed_methods = tuple(name for name in candidates if self.allows_method(name))
        return allowed_methods

    def NOT_ALLOWED(self):
        raise HTTPMethodNotAllowed()

    def OPTIONS(self):
        """Get resource options.

        By default, this will add an ``Allow`` header to the response
        that lists the methods implemented by the resource.

        """
        response = Response()
        allowed_methods = self.allowed_methods
        if allowed_methods:
            response.allow = ', '.join(allowed_methods)
        return response

    DELETE = NOT_ALLOWED
    """Delete resource.

    Return

        - 204 if no body
        - 200 if body
        - 202 if accepted but not yet deleted

    """

    GET = NOT_ALLOWED
    """Get resource.

    Return:

        - 200 body

    """

    HEAD = NOT_ALLOWED
    """Get resource metadata.

    Return:

        - 204 no body (same headers as GET)

    """

    POST = NOT_ALLOWED
    """Create a new child resource.

    Return:

        - If resource created and identifiable w/ URL:
            - 201 w/ body and Location header (for XHR?)
            - 303 w/ Location header (for browser?)
        - If resource not identifiable:
            - 200 if body
            - 204 if no body

    """

    PUT = NOT_ALLOWED
    """Update resource or create if it doesn't exist.

    Return:

        - If new resource created, same as :meth:`POST`
        - If updated:
            - 200 (body)
            - 204 (no body)
            - 303 (instead of 204)

    """

    PATCH = NOT_ALLOWED
    """Update resource.

    Return:

        - 200 (body)
        - 204 (no body)
        - 303 (instead of 204)

    """
