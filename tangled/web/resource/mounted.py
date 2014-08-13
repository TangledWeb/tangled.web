import re
import sys
from collections import namedtuple, OrderedDict

from tangled.converters import get_converter, as_tuple
from tangled.util import load_object

from ..abcs import AMountedResourceTree


Match = namedtuple('Match', ('mounted_resource', 'urlvars'))


class MountedResourceTree(AMountedResourceTree):

    def __init__(self):
        self.root = Node(None, None)
        self.height = 0
        self.min_height = sys.maxsize

    def add(self, mounted_resource):
        tree = self.root
        segments = mounted_resource.segments
        height = min_height = len(segments)
        for segment in segments:
            tree = tree.make_child(segment)
        tree.mounted_resources.append(mounted_resource)
        if mounted_resource.add_slash:
            tree = tree.make_child('')
            tree.mounted_resources.append(mounted_resource)
            height += 1
        if height > self.height:
            self.height = height
        if min_height < self.min_height:
            self.min_height = min_height

    def find(self, method, path):
        segments = path.lstrip('/').split('/')
        num_segments = len(segments)
        if num_segments > self.height or num_segments < self.min_height:
            return None  # Short circuit if a match isn't possible
        tree = self.root
        stack = [[{}, 0]]
        while tree:
            stack_top = stack[-1]
            segment = segments[len(stack) - 1]
            for child in tree.child_list(stack_top[1]):
                stack_top[1] += 1
                match = re.search(child.regex, segment)
                if match:
                    stack.append([match.groupdict(), 0])
                    if len(stack) > num_segments:
                        for mounted_resource in child.mounted_resources:
                            if mounted_resource.responds_to(method):
                                urlvars = {}
                                for item in stack:
                                    urlvars.update(item[0])
                                urlvars_info = mounted_resource.urlvars_info
                                for k in urlvars_info:
                                    converter = urlvars_info[k]['converter']
                                    urlvars[k] = converter(urlvars[k])
                                return Match(mounted_resource, urlvars)
                        stack.pop()
                    else:
                        tree = child
                        break
            else:
                # Traversed across all children without finding a match.
                # Go back up to the parent and continue traversing its
                # children.
                tree = tree.parent
                stack.pop()

    def __str__(self):
        return str(self.root)


class Node:

    def __init__(self, parent, segment):
        self.parent = parent
        self.children = OrderedDict()
        if segment is None:
            self.regex = None
        else:
            self.regex = re.compile(r'^{}$'.format(segment))

        # Multiple resources can be mounted at the same path responding
        # to different methods. This is necessary for the case where a
        # request method is mapped to a resource method with a different
        # name (i.e., when a method_name is passed to MountedResource).
        self.mounted_resources = []

    def make_child(self, segment):
        child = self.children.get(segment)
        if child is None:
            child = self.__class__(self, segment)
            self.children[segment] = child
        return child

    def child_list(self, i=0):
        child_list = list(self.children.values())
        if i != 0:
            child_list = child_list[i:]
        return child_list

    def __iter__(self):
        return iter(self.children.values())

    def __str__(self):
        s = []
        tree = self
        children = tree.child_list()
        level = 0
        while children:
            next_children = []
            s.append('    ' * level)
            s.append('{}: '.format(tree.regex.pattern))
            for child in children:
                mounted_resource = child.mounted_resource
                if mounted_resource is not None:
                    s.append(mounted_resource.path_regex + ' ')
                next_children.extend(child.child_list())
                s.append(child.regex.pattern + ' | ')
            s.append('\n')
            children = next_children
            level += 1
        return ''.join(s).strip()


class MountedResource:

    # URL var format: (converter)identifier:regex
    urlvar_regex = (
        r'<'
        '(?:\((?P<converter>[^\d\W][\w.:]*)\)?)?'  # Optional converter
        '(?P<identifier>[^\d\W]\w*)'               # Any valid Python identifier
        '(?::(?P<regex>[^/<>]+))?'                 # Optional regular expression
        '>'
    )

    def __init__(self, name, factory, path, methods=(), method_name=None,
                 add_slash=False):
        if not path.startswith('/'):
            path = '/' + path

        if path == '/':
            add_slash = False
        else:
            add_slash = True if path.endswith('/') else add_slash

        self.name = name
        self.factory = factory
        self.path = path
        self.methods = set(as_tuple(methods, sep=','))
        self.method_name = method_name
        self.add_slash = add_slash

        if add_slash:
            path = path.rstrip('/')

        urlvars_info = {}
        path_regex = []
        format_string = []
        i = 0

        for match in re.finditer(self.urlvar_regex, path):
            info = match.groupdict()
            identifier = info['identifier']

            if identifier in urlvars_info:
                raise ValueError('{} already present'.format(identifier))

            regex = info['regex'] or r'[\w-]+'

            converter = info['converter']
            if converter:
                if ':' in converter:
                    converter = load_object(converter)
                else:
                    converter = get_converter(converter)
            else:
                converter = str

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

        path_regex = ''.join(path_regex)
        self.segments = path_regex.strip('/').split('/')

        if add_slash:
            path_regex += r'(?:/?)'
            format_string.append('/')

        self.urlvars_info = urlvars_info
        self.path_regex = path_regex
        self.format_string = ''.join(format_string)

    def responds_to(self, method):
        return not self.methods or method in self.methods

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
