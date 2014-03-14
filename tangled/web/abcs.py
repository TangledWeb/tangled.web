from abc import ABCMeta


class AApplication(metaclass=ABCMeta):

    """Just a marker for now."""


class AAppSettings(metaclass=ABCMeta):

    """Just a marker for now."""


class AHandler(metaclass=ABCMeta):

    """Just a marker for now."""


class AHelpers(metaclass=ABCMeta):

    def __init__(self, app, request):
        self.app = app
        self.request = request


class ARequest(metaclass=ABCMeta):

    """Just a marker for now."""


class AResponse(metaclass=ABCMeta):

    """Just a marker for now."""


class AMountedResource(metaclass=ABCMeta):

    """Just a marker for now."""
