import unittest

from tangled.util import load_object

from tangled.web import Application
from tangled.web.handlers import resource_finder
from tangled.web.resource.mounted import MountedResourceTree, MountedResource


class TestMountedResouce(unittest.TestCase):

    def test_path_parsing(self):
        path = '/<path><name:[a-z]{3}>/<(int)id:\d+>.<format:[a-z]+>;extra'
        mr = MountedResource('test', None, path)

        info = mr.urlvars_info
        self.assertEqual(info['path'], {'regex': '[\w-]+', 'converter': str})
        self.assertEqual(info['name'], {'regex': '[a-z]{3}', 'converter': str})
        self.assertEqual(info['id'], {'regex': '\d+', 'converter': int})
        self.assertEqual(info['format'], {'regex': '[a-z]+', 'converter': str})

        format_string = mr.format_string
        self.assertEqual(format_string, '/{path}{name}/{id}.{format};extra')

    def test_converter_specified_by_path(self):
        path = '/<(tangled.util:load_object)obj>'
        mr = MountedResource('test', None, path)
        info = mr.urlvars_info
        self.assertIs(info['obj']['converter'], load_object)
        self.assertEqual(
            mr.format_path(obj='collections:OrderedDict'),
            '/collections:OrderedDict')

    def test_bad_converter(self):
        path = '/<(duhr)id>'
        with self.assertRaises(TypeError):
            MountedResource('test', None, path)
        path = '/<(tangled.util:duhr)obj>'
        with self.assertRaises(AttributeError):
            MountedResource('test', None, path)

    def test_format_path(self):
        path = '/<path><name:[a-z]{3}>/<(int)id:\d+>.<format:[a-z]+>;extra'
        mr = MountedResource('test', None, path)
        self.assertEqual(
            mr.format_path(path='somewhere', name='bob', id=13, format='json'),
            '/somewherebob/13.json;extra')

    def test_format_path_unknown_var(self):
        path = '/<path><name:[a-z]{3}>/<(int)id:\d+>.<format:[a-z]+>;extra'
        mr = MountedResource('test', None, path)
        with self.assertRaises(ValueError):
            mr.format_path(pat='somewhere', name='bob', id=13, format='json')

    def test_format_path_bad_value(self):
        path = '/<path><name:[a-z]{3}>/<(int)id:\d+>.<format:[a-z]+>;extra'
        mr = MountedResource('test', None, path)
        with self.assertRaises(ValueError):
            mr.format_path(path='somewhere', name='bob', id='x', format='json')

    def test_add_slash(self):
        path = '/some/dir/'
        mr = MountedResource('test', None, path)
        self.assertTrue(mr.add_slash)
        self.assertEqual(mr.format_path(), '/some/dir/')

        tree = MountedResourceTree()
        tree.add(mr)
        tree.find('GET', '/some/dir/')

        match = tree.find('GET', '/some/dir/')
        self.assertIsNotNone(match)
        self.assertIs(match.mounted_resource, mr)

        match = tree.find('GET', '/some/dir')
        self.assertIsNotNone(match)
        self.assertIs(match.mounted_resource, mr)

    def test_add_slash_redirect(self):
        app = Application({})
        factory = lambda *args: type('Resource', (), {'GET': None})
        app.mount_resource('test', factory, '/some/dir', add_slash=True)

        # Should not redirect
        next_handler = lambda app_, request_: 'NEXT'
        request = app.make_blank_request('/some/dir/')
        self.assertEqual(resource_finder(app, request, next_handler), 'NEXT')

        # Should redirect
        request = app.make_blank_request('/some/dir')
        try:
            resource_finder(app, request, next_handler)
        except Exception as exc:
            self.assertTrue(exc.status.startswith('3'))
            self.assertTrue(exc.location.endswith('/some/dir/'))


class TestMountedResourceTree(unittest.TestCase):

    def setUp(self):
        tree = MountedResourceTree(cache_size=2)
        tree.add(MountedResource('home', None, '/'))
        tree.add(MountedResource('a', None, '/a'))
        tree.add(MountedResource('b', None, '/b/'))
        tree.add(MountedResource('xyz', None, '/x/<y>/z', methods='GET'))
        tree.add(MountedResource('xkz', None, '/x/k/z'))
        tree.add(MountedResource('y_get', None, '/y', methods='GET'))
        tree.add(MountedResource('y_post', None, '/y', methods='POST'))
        tree.add(MountedResource('cached', None, '/cached'))
        tree.add(MountedResource('catch-all', None, '/<x>', methods='GET'))
        self.tree = tree

    def test_find_home(self):
        match = self.tree.find('GET', '/')
        self.assertIsNotNone(match)
        mr = match.mounted_resource
        self.assertEqual(mr.name, 'home')

    def test_find_a(self):
        match = self.tree.find('GET', '/a')
        self.assertIsNotNone(match)
        mr = match.mounted_resource
        self.assertEqual(mr.name, 'a')

    def test_find_a_post(self):
        match = self.tree.find('POST', '/a')
        self.assertIsNotNone(match)
        mr = match.mounted_resource
        self.assertEqual(mr.name, 'a')

    def test_find_add_slash(self):
        for path in ('/b/', '/b'):
            match = self.tree.find('GET', path)
            self.assertIsNotNone(match)
            mr = match.mounted_resource
            self.assertEqual(mr.name, 'b')

    def test_find_x(self):
        match = self.tree.find('GET', '/x')
        self.assertIsNotNone(match)
        mr = match.mounted_resource
        self.assertEqual(mr.name, 'catch-all')

    def test_find_xyz(self):
        match = self.tree.find('GET', '/x/y/z')
        self.assertIsNotNone(match)
        mr = match.mounted_resource
        self.assertEqual(mr.name, 'xyz')

    def test_not_found(self):
        match = self.tree.find('GET', '/x/y')
        self.assertIsNone(match)

    def test_not_found_method(self):
        match = self.tree.find('POST', '/x/y/z')
        self.assertIsNone(match)

    def test_long_not_found(self):
        match = self.tree.find('GET', '/x/y/z/a/b/c')
        self.assertIsNone(match)

    def test_short_not_found(self):
        tree = MountedResourceTree()
        tree.add(MountedResource('abc', None, '/a/b/c'))
        tree.add(MountedResource('xyz', None, '/<x>/<y>/<z>'))
        tree.find('GET', '/a/b')

    def test_find_y_get(self):
        match = self.tree.find('GET', '/y')
        self.assertIsNotNone(match)
        mr = match.mounted_resource
        self.assertEqual(mr.name, 'y_get')

    def test_find_y_post(self):
        match = self.tree.find('POST', '/y')
        self.assertIsNotNone(match)
        mr = match.mounted_resource
        self.assertEqual(mr.name, 'y_post')

    def test_find_lru_cache(self):
        self.tree.find.cache_clear()
        method, path = 'GET', '/cached'
        match = self.tree.find(method, path)
        self.assertIsNotNone(match)
        cache_info = self.tree.find.cache_info()
        self.assertEqual(cache_info.hits, 0)
        self.assertEqual(cache_info.misses, 1)
        match = self.tree.find(method, path)
        self.assertIsNotNone(match)
        cache_info = self.tree.find.cache_info()
        self.assertEqual(cache_info.hits, 1)
        self.assertEqual(cache_info.misses, 1)
