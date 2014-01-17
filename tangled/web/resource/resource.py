from webob.exc import HTTPMethodNotAllowed


class Resource:

    """Resource type.

    When creating your own resources, it's not strictly necessary to
    subclass this type.

    """

    def __init__(self, app, request, name=None, urlvars=None):
        self.app = app
        self.request = request
        self.name = name
        self.urlvars = urlvars

    def url(self, urlvars=None, **kwargs):
        urlvars = self.urlvars if urlvars is None else urlvars
        return self.request.resource_url(self, urlvars, **kwargs)

    def path(self, urlvars=None, **kwargs):
        urlvars = self.urlvars if urlvars is None else urlvars
        return self.request.resource_path(self, urlvars, **kwargs)

    def NOT_ALLOWED(self):
        raise HTTPMethodNotAllowed()

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

    OPTIONS = NOT_ALLOWED
    """Get resource options.

    Return:

        - ???

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
