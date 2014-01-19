from webob.static import DirectoryApp as LocalDirectory


class RemoteDirectory:

    def __init__(self, path):
        self.path = path
