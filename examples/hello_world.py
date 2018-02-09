from wsgiref.simple_server import make_server

from tangled.web import Application, Resource


class Home(Resource):

    def GET(self):
        path = self.request.resource_path('hello', {'name': 'World'})
        return (
            'Welcome to the example. '
            'Click <a href="{path}">here</a> for a greeting.'
        ).format_map(locals())


class Hello(Resource):

    def GET(self, name, greeting=None):
        action = self.request.path
        greeting = greeting or 'Hello'
        home_path = self.request.resource_path('home')
        return (
            '<p><a href="{home_path}">Home</a>'
            '<p>{greeting}, {name}</p>'
            '<p><small>Note: Set name via URL</small></p>'
            '<form method="get" action="{action}">'
            '    <input name="greeting" type="text" placeholder="Greeting">'
            '    <button type="submit">Greet</button>'
            '</form>'
        ).format_map(locals())


def on_created(event):
    # Make a request to the root of the example app after it's created.
    print('Example request and response:\n')
    request = event.app.make_blank_request('/')
    response = event.app.handle_request(request)
    print(request, response, sep='\n\n')


if __name__ == '__main__':
    settings = {
        'debug': True,
        'tangled.app.on_created': [on_created],
        'tangled.app.defer_created': True,
    }

    app = Application(settings)
    app.mount_resource('home', Home, '/')

    # Greet user with "Hello" by default. The user's name must be passed
    # as a URL arg. A different greeting can be passed as the greeting
    # query parameter.
    app.mount_resource('hello', Hello, '/hello/<name>')

    # Greet with a specific greeting. Both the user's name and the
    # greeting must be passed as URL args.
    app.mount_resource('greet', Hello, '/greet/<name>/<greeting>')

    # Fire on-created event to initiate the example request.
    app.created()

    server = make_server('0.0.0.0', 6666, app)
    server.serve_forever()
