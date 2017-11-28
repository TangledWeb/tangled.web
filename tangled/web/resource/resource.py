from webob.exc import HTTPMethodNotAllowed

from tangled.web.response import Response


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

    def __init__(self, app, request, name=None, urlvars=None):
        self.app = app
        self.request = request
        self.name = name
        self.urlvars = urlvars

    def url(self, urlvars=None, **kwargs):
        """Generate a fully qualified URL for this resource.

        You can pass ``urlvars``, ``query``, and/or ``fragment`` to
        generate a URL based on this resource.

        """
        urlvars = self.urlvars if urlvars is None else urlvars
        return self.request.resource_url(self, urlvars, **kwargs)

    def path(self, urlvars=None, **kwargs):
        """Generate an application-relative URL path for this resource.

        You can pass ``urlvars``, ``query``, and/or ``fragment`` to
        generate a path based on this resource.

        """
        urlvars = self.urlvars if urlvars is None else urlvars
        return self.request.resource_path(self, urlvars, **kwargs)

    def allows_method(self, method):
        method = getattr(self, method, None)
        return not (
            method is None or
            method.__func__ is self.__class__.NOT_ALLOWED
        )

    @property
    def allowed_methods(self):
        methods = ('OPTIONS', 'GET', 'HEAD', 'POST', 'PUT', 'PATCH')
        allowed_methods = [m for m in methods if self.allows_method(m)]
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
