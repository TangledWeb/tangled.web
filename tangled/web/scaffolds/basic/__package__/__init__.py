def include(app):
    """Configure ${package_name}."""
    app.mount_resource('home', '.resources:Hello', '/', methods='GET')
    app.mount_resource('hello', '.resources:Hello', '/<name>', methods='GET')
    return app
