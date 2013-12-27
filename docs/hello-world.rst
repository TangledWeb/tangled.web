Hello, World
++++++++++++

Here's a really simple Tangled Web app:

.. code-block:: python

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
            'tangled.app.csrf.enabled': False,
        }
        app = Application(settings)
        app.mount_resource('hello', Hello, '/')
        app.mount_resource('hello_name', Hello, '/{name}')
        server = make_server('0.0.0.0', 6666, app)
        server.serve_forever()


.. note::
    This is a copy of ``examples/hello_world.py``. If you're in the top level
    of ``tangled.web`` checkout, you can run it with
    ``python examples/hello_world.py`` (assuming ``tangled.web`` is already
    installed).
