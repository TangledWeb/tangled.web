from wsgiref.simple_server import make_server

from tangled.web import Application, Resource


class Hello(Resource):

    def GET(self):
        if 'name' in self.urlvars:
            content = 'Hello, {name}'.format(**self.urlvars)
        else:
            content = 'Hello'
        return content


if __name__ == '__main__':
    settings = {
        'debug': True,
    }
    app = Application(settings)
    app.mount_resource('hello', Hello, '/')
    app.mount_resource('hello_name', Hello, '/<name>')
    server = make_server('0.0.0.0', 6666, app)
    server.serve_forever()
