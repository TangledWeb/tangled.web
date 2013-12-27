import sys


class Subscriber:

    def __init__(self, event_type, func, priority=None, once=False, args=None):
        self.event_type = event_type
        self.func = func
        self.priority = sys.maxsize if priority is None else priority
        self.once = once
        self.args = args or {}  # Passed as kwargs to func

    @staticmethod
    def sorter(subscriber):
        return subscriber.priority


class ApplicationCreated:

    def __init__(self, app):
        self.app = app


class NewRequest:

    def __init__(self, app, request):
        self.app = app
        self.request = request


class ResourceFound:

    def __init__(self, app, request, resource):
        self.app = app
        self.request = request
        self.resource = resource


class NewResponse:

    def __init__(self, app, request, response):
        self.app = app
        self.request = request
        self.response = response


class TemplateContextCreated:

    def __init__(self, app, request, context):
        self.app = app
        self.request = request
        self.context = context
