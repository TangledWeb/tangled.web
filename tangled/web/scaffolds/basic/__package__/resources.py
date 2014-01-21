from tangled.web import config, Resource


class Hello(Resource):

    @config('text/html', type='string')
    def GET(self):
        name = self.urlvars.get('name', 'World')
        return 'Hello, {name}'.format(name=name)
