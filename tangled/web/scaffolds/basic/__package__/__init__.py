from tangled.web import Application


def make_app(settings):
    """Configure ${package_name}."""
    app = Application(settings)
    app.mount_resource('home', '.resources:Hello', '/', methods='GET')
    app.mount_resource('hello', '.resources:Hello', '/<name>', methods='GET')
    return app
