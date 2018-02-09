import collections
import re


MountedResourceMatch = collections.namedtuple('MountedResourceMatch', 'mounted_resource urlvars')


class MountedResource:

    urlvar_regex = r'<(?P<identifier>[^\d\W]\w*)>'

    def __init__(self, app, name, factory, path, methods=(), method=None, add_slash=False):
        if not path.startswith('/'):
            raise ValueError('Path must begin with a slash: {path}'.format_map(locals()))

        if '//' in path:
            raise ValueError('Path contains an empty segment: {path}'.format_map(locals()))

        if path == '/':
            add_slash = False
        elif path.endswith('/'):
            add_slash = True
        elif add_slash:
            path = '{path}/'.format_map(locals())

        if not methods:
            resource = factory(app, None, name)
            methods = resource.allowed_methods
        elif isinstance(methods, str):
            methods = (methods,)
        else:
            methods = tuple(methods)

        self.name = name
        self.factory = factory
        self.path = path  # normalized path
        self.methods = set(methods)
        self.method = method
        self.add_slash = add_slash

        urlvars = []
        path_regex = ['^']
        format_string = []
        i = 0

        for match in re.finditer(self.urlvar_regex, path):
            identifier = match.group('identifier')

            if identifier in urlvars:
                raise ValueError(
                    'Duplicate URL var in path {path}: {identifier}'.format_map(locals()))

            urlvars.append(identifier)

            # Get the non-matching part of the string after the previous
            # match and before the current match.
            start, end = match.span()

            if i != start:
                before_match = path[i:start]
                path_regex.append(before_match)
                format_string.append(before_match)

            i = end

            path_regex.append('(?P<{identifier}>[^/]+)'.format_map(locals()))
            format_string.extend(('{', identifier, '}'))

        if i != len(path):
            remainder = path[i:]
            path_regex.append(remainder)
            format_string.append(remainder)

        path_regex = ''.join(path_regex)
        format_string = ''.join(format_string)

        if add_slash:
            path_regex = '{path_regex}(?:/?)'.format(path_regex=path_regex.rstrip('/'))

        path_regex = '{path_regex}$'.format_map(locals())
        path_regex = re.compile(path_regex)

        self.urlvars = urlvars
        self.path_regex = path_regex
        self.format_string = format_string

    def format_path(self, **args):
        """Format the resource path with the specified args."""
        for k, v in args.items():
            if k not in self.urlvars:
                raise ValueError('Unknown URL var: {}'.format(k))
            # TODO: Check that args are valid
        return self.format_string.format(**args)

    def __repr__(self):
        return (
            '{self.__class__.__name__}('
            'name={self.name}, '
            'factory={self.factory}, '
            'path={self.path}, '
            'methods={self.methods}, '
            'method={self.method}, '
            'add_slash={self.add_slash}'
            ')'
        ).format(self=self)
