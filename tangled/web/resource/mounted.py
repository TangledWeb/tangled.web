import re
from collections import namedtuple

from tangled.converters import get_converter, as_tuple


Match = namedtuple('Match', ('mounted_resource', 'urlvars'))


class MountedResource:

    # URL var format: (converter)identifier:regex
    urlvar_regex = (
        r'<'
        '(?:\((?P<converter>[a-z]+)\)?)?'  # Optional converter
        '(?P<identifier>[^\d\W]\w*)'       # Any valid Python identifier
        '(?::(?P<regex>[^/<>]+))?'         # Optional regular expression
        '>'
    )

    def __init__(self, name, factory, path, methods=(), method_name=None,
                 add_slash=False):
        self.name = name
        self.factory = factory
        self.path = path
        self.methods = set(as_tuple(methods, sep=','))
        self.method_name = method_name
        self.add_slash = add_slash = True if path.endswith('/') else add_slash

        if not path.startswith('/'):
            path = '/' + path

        if add_slash:
            path = path.rstrip('/')

        urlvars_info = {}
        path_regex = ['^']
        format_string = []
        i = 0

        for match in re.finditer(self.urlvar_regex, path):
            info = match.groupdict()
            identifier = info['identifier']

            if identifier in urlvars_info:
                raise ValueError('{} already present'.format(identifier))

            regex = info['regex'] or r'[\w-]+'
            converter = info['converter']
            converter = get_converter(converter) if converter else str
            urlvars_info[identifier] = {'regex': regex, 'converter': converter}

            # Get the non-matching part of the string after the previous
            # match and before the current match.
            s, e = match.span()
            if i != s:
                before_match = path[i:s]
                path_regex.append(before_match)
                format_string.append(before_match)
            i = e

            path_regex.append(r'(?P<{}>{})'.format(identifier, regex))
            format_string.extend(('{', identifier, '}'))

        if i != len(path):
            remainder = path[i:]
            path_regex.append(remainder)
            format_string.append(remainder)

        if add_slash:
            path_regex.append(r'(?:/?)')
            format_string.append('/')

        path_regex.append('$')
        path_regex = ''.join(path_regex)

        self.urlvars_info = urlvars_info
        self.path_regex = re.compile(path_regex)
        self.format_string = ''.join(format_string)

    def match(self, method, path):
        if self.methods and method not in self.methods:
            return None
        match = self.path_regex.search(path)
        if match:
            urlvars = match.groupdict()
            for k in urlvars:
                converter = self.urlvars_info[k]['converter']
                urlvars[k] = converter(urlvars[k])
            return Match(self, urlvars)

    def match_request(self, request):
        return self.match(request.method, request.path_info)

    def format_path(self, **args):
        """Format the resource path with the specified args."""
        for k, v in args.items():
            if k not in self.urlvars_info:
                raise ValueError('Unknown URL var: {}'.format(k))
            converter = self.urlvars_info[k]['converter']
            try:
                converter(v)
            except ValueError:
                raise ValueError(
                    'Could not convert `{}` for URL var {}'.format(v, k))
        return self.format_string.format(**args)
