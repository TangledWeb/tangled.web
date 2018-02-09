class BindError(Exception):

    def __init__(self, resource, request, method, exc):
        self.resource = resource
        self.request = request
        self.method = method
        self.exc = exc

    def __str__(self):
        string = 'Could not bind request to resource method {self.method}: {self.exc}'
        string = string.format(self=self)
        return string
