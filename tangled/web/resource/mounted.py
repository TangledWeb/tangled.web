import logging
import re
from collections import namedtuple, OrderedDict
from functools import lru_cache

from tangled.converters import get_converter, as_tuple
from tangled.util import load_object

from ..abcs import AMountedResourceTree


log = logging.getLogger(__name__)


Match = namedtuple('Match', ('mounted_resource', 'urlvars'))


class MountedResourceTree(AMountedResourceTree):

    def __init__(self, cache_size=64):
        self.root = Node(None, None)
        if cache_size:
            self.find = lru_cache(cache_size)(self.find)

    def add(self, mounted_resource):
        tree = self.root
        segments = mounted_resource.segments
        add_slash = mounted_resource.add_slash
        depth = len(segments)
        for segment in segments:
            tree.resource_depths.add(depth)
            if add_slash:
                tree.resource_depths.add(depth + 1)
            tree = tree.make_child(segment)
            depth -= 1
        assert depth == 0
        tree.resource_depths.add(0)
        tree.mounted_resources.append(mounted_resource)
        if add_slash:
            tree.resource_depths.add(1)
            tree = tree.make_child('')
            tree.resource_depths.add(0)
            tree.mounted_resources.append(mounted_resource)

    def find(self, method, path):
        tree = self.root
        segments = path.lstrip('/').split('/')
        height = len(segments)
        if height not in tree.resource_depths:
            return None  # Short circuit if a match isn't possible
        stack = [[{}, 0]]
        while tree:
            stack_top = stack[-1]
            stack_len = len(stack)
            depth = height - stack_len
            segment = segments[stack_len - 1]
            for child in tree.child_list(stack_top[1]):
                stack_top[1] += 1
                if depth not in child.resource_depths:
                    continue  # Short circuit if a match isn't possible
                match = re.search(child.regex, segment)
                if match:
                    stack.append([match.groupdict(), 0])
                    if len(stack) > height:
                        for mounted_resource in child.mounted_resources:
                            if mounted_resource.responds_to(method):
                                urlvars = {}
                                for item in stack:
                                    urlvars.update(item[0])
                                urlvars_info = mounted_resource.urlvars_info
                                for k in urlvars_info:
                                    converter = urlvars_info[k]['converter']
                                    urlvars[k] = converter(urlvars[k])
                                match = Match(mounted_resource, urlvars)
                                return match
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

        # Depths where resources are mounted (relative to this node).
        self.resource_depths = set()

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
            if path.endswith('/'):
                add_slash = True
            elif add_slash:
                path = '{}/'.format(path)

        self.name = name
        self.factory = factory
        self.path = path  # normalized path
        self.methods = set(as_tuple(methods, sep=','))
        self.method_name = method_name
        self.add_slash = add_slash

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

        self.urlvars_info = urlvars_info
        self.segments = path_regex.strip('/').split('/')
        self.format_string = ''.join(format_string)

        if add_slash:
            path_regex = r'{}(?:/?)'.format(path_regex.rstrip('/'))

        self.path_regex = path_regex

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
