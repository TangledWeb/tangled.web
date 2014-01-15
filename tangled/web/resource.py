import collections
import posixpath
import re

from webob.exc import HTTPMethodNotAllowed

from tangled.converters import as_tuple
from tangled.decorators import reify
from tangled.util import load_object


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


Match = collections.namedtuple('Match', ('name', 'factory', 'path', 'urlvars'))


class MountedResource:

    identifier = r'{(?!.*\d+.*)(\w+)}'
    identifier_with_re = r'{(?!.*\d+.*)(\w+):(.*)}'

    def __init__(self, name, factory, path, methods=()):
        self.name = name
        self.factory = load_object(factory, level=4)
        self.path = path
        self.methods = set(as_tuple(methods, sep=','))
        self.path_regex  # Ensure valid

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_traceback):
        return False

    @reify
    def path_regex(self):
        path = self.path
        if not path.startswith('/'):
            path = '/' + path
        regex = re.sub(self.identifier, r'(?P<\1>\w+)', path)
        regex = re.sub(self.identifier_with_re, r'(?P<\1>\2)', regex)
        regex = r'^{}$'.format(regex)
        regex = re.compile(regex)
        return regex

    @reify
    def format_string(self):
        path = self.path
        if not path.startswith('/'):
            path = '/' + path
        format_string = re.sub(self.identifier, r'{\1}', path)
        format_string = re.sub(self.identifier_with_re, r'{\1}', format_string)
        return format_string

    def match(self, method, path):
        if self.methods and method not in self.methods:
            return None
        match = self.path_regex.search(path)
        if match:
            return Match(self.name, self.factory, self.path, match.groupdict())

    def match_request(self, request):
        return self.match(request.method, request.path_info)

    def format_path(self, **args):
        """Format the resource path with the specified args."""
        path = self.format_string.format(**args)
        if not self.path_regex.search(path):
            raise ValueError(
                'Invalid substitions: {} for {}'.format(args, path))
        return path

    def mount(self, name, factory, path):
        """Mount subresource.

        This can be used like this::

            r = app.mount_resource(...)
            r.mount(...)

        and like this::

            with app.mount_resource(...) as r:
                r.mount(...)

        In either case, the subresource's path will be prepended with
        its parent's path.

        """
        path = posixpath.join(self.path, path.lstrip('/'))
        return self.container.mount(name, factory, path)