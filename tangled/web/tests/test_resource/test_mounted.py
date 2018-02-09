import unittest

from tangled.web import Application, Resource
from tangled.web.handlers import resource_finder
from tangled.web.resource.mounted import MountedResource


class TestResource(Resource):

    def GET(self, *args, **kwargs):
        pass

    def POST(self, *args, **kwargs):
        pass


class TestMountedResource(unittest.TestCase):

    def setUp(self):
        self.app = Application({})

    def test_path_parsing(self):
        path = '/<path><name>/<id>.<format>;extra'

        mr = MountedResource(self.app, 'test', TestResource, path)
        self.assertEqual(mr.urlvars, ['path', 'name', 'id', 'format'])

        format_string = mr.format_string
        self.assertEqual(format_string, '/{path}{name}/{id}.{format};extra')

    def test_format_path(self):
        path = '/<path><name>/<id>.<format>;extra'
        mr = MountedResource(self.app, 'test', TestResource, path)
        self.assertEqual(
            mr.format_path(path='somewhere', name='bob', id=13, format='json'),
            '/somewherebob/13.json;extra')

    def test_format_path_unknown_var(self):
        path = '/<path><name>/<id>.<format>;extra'
        mr = MountedResource(self.app, 'test', TestResource, path)
        with self.assertRaises(ValueError):
            mr.format_path(pat='somewhere', name='bob', id=13, format='json')

    def test_format_path_bad_value(self):
        path = '/<path><name>/<id:int>.<format>;extra'
        mr = MountedResource(self.app, 'test', TestResource, path)
        with self.assertRaises(ValueError):
            mr.format_path(path='somewhere', name='bob', id='x', format='json')

    def test_add_slash(self):
        app = self.app
        path = '/some/dir/'
        mr = MountedResource(app, 'test', TestResource, path)
        self.assertTrue(mr.add_slash)
        self.assertEqual(mr.format_path(), '/some/dir/')

    def test_add_slash_find(self):
        app = self.app
        sub_resource_mounter = app.mount_resource('test', TestResource, '/some/dir/')
        mr = sub_resource_mounter.parent

        match = app.find_mounted_resource('GET', '/some/dir/')
        self.assertIsNotNone(match)
        self.assertIs(match.mounted_resource, mr)

        match = app.find_mounted_resource('GET', '/some/dir')
        self.assertIsNotNone(match)
        self.assertIs(match.mounted_resource, mr)

    def test_add_slash_redirect(self):
        app = self.app
        app.mount_resource('test', TestResource, '/some/dir', add_slash=True)

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
        app = Application({})
        app.mount_resource('home', TestResource, '/')
        app.mount_resource('catch-all-single-segment-paths', TestResource, '/<x>', methods='GET')
        app.mount_resource('a', TestResource, '/a')
        app.mount_resource('b', TestResource, '/b/')
        app.mount_resource('abc', TestResource, '/a/b/c')
        app.mount_resource('abc_any', TestResource, '/<a>/<b>/<c>')
        app.mount_resource('xyz', TestResource, '/x/<y>/z', methods='GET')
        app.mount_resource('xkz', TestResource, '/x/k/z')
        app.mount_resource('y_get', TestResource, '/y', methods='GET')
        app.mount_resource('y_post', TestResource, '/y', methods='POST')
        app.mount_resource('cached', TestResource, '/cached')
        self.app = app

    def test_find_home(self):
        match = self.app.find_mounted_resource('GET', '/')
        self.assertIsNotNone(match)
        mr = match.mounted_resource
        self.assertEqual(mr.name, 'home')

    def test_find_a(self):
        match = self.app.find_mounted_resource('GET', '/a')
        self.assertIsNotNone(match)
        mr = match.mounted_resource
        self.assertEqual(mr.name, 'a')

    def test_find_a_post(self):
        match = self.app.find_mounted_resource('POST', '/a')
        self.assertIsNotNone(match)
        mr = match.mounted_resource
        self.assertEqual(mr.name, 'a')

    def test_find_add_slash(self):
        for path in ('/b/', '/b'):
            match = self.app.find_mounted_resource('GET', path)
            self.assertIsNotNone(match)
            mr = match.mounted_resource
            self.assertEqual(mr.name, 'b')

    def test_find_x(self):
        match = self.app.find_mounted_resource('GET', '/x')
        self.assertIsNotNone(match)
        mr = match.mounted_resource
        self.assertEqual(mr.name, 'catch-all-single-segment-paths')

    def test_find_xyz(self):
        match = self.app.find_mounted_resource('GET', '/x/y/z')
        self.assertIsNotNone(match)
        mr = match.mounted_resource
        self.assertEqual(mr.name, 'xyz')

    def test_not_found(self):
        match = self.app.find_mounted_resource('GET', '/x/y')
        self.assertIsNone(match)

    def test_not_found_method(self):
        match = self.app.find_mounted_resource('PUT', '/x/y/z')
        self.assertIsNone(match)

    def test_long_not_found(self):
        match = self.app.find_mounted_resource('GET', '/x/y/z/a/b/c')
        self.assertIsNone(match)

    def test_short_not_found(self):
        app = self.app
        match = app.find_mounted_resource('GET', '/a/b')
        self.assertIsNone(match)

    def test_find_y_get(self):
        match = self.app.find_mounted_resource('GET', '/y')
        self.assertIsNotNone(match)
        mr = match.mounted_resource
        self.assertEqual(mr.name, 'y_get')

    def test_find_y_post(self):
        match = self.app.find_mounted_resource('POST', '/y')
        self.assertIsNotNone(match)
        mr = match.mounted_resource
        self.assertEqual(mr.name, 'y_post')

    def test_find_lru_cache(self):
        self.app.find_mounted_resource.cache_clear()
        method, path = 'GET', '/cached'
        match = self.app.find_mounted_resource(method, path)
        self.assertIsNotNone(match)
        cache_info = self.app.find_mounted_resource.cache_info()
        self.assertEqual(cache_info.hits, 0)
        self.assertEqual(cache_info.misses, 1)
        match = self.app.find_mounted_resource(method, path)
        self.assertIsNotNone(match)
        cache_info = self.app.find_mounted_resource.cache_info()
        self.assertEqual(cache_info.hits, 1)
        self.assertEqual(cache_info.misses, 1)
