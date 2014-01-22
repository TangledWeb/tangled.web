"""Events are registered in the context of an application via
:meth:`tangled.web.app.Application.add_subscriber`.

Subscribers typically have the signature ``subscriber(event)``. If subscriber
keyword args were passed to ``add_subscriber``, then the signature for the
subscriber would be ``subscriber(event, **kwargs)``.

Every event object will have an ``app`` attribute. Other attributes are
event dependent.

"""
import sys

import venusian


class subscriber:

    """Decorator for adding event subscribers.

    Subscribers registered this way won't be activated until a scan is
    done via :meth:`tangled.web.app.Application.scan`.

    Example::

        @subscriber('tangled.web.events:ResourceFound')
        def on_resource_found(event):
            log.debug(event.resource.name)

    """

    def __init__(self, event_type, *args, **kwargs):
        self.event_type = event_type
        self.args = args
        self.kwargs = kwargs

    def __call__(self, wrapped):
        def venusian_callback(scanner, *_):
            app = scanner.app
            app.add_subscriber(
                self.event_type, wrapped, *self.args, **self.kwargs)
        venusian.attach(wrapped, venusian_callback, category='tangled')
        return wrapped


class ApplicationCreated:

    """Emitted when an application is fully configured.

    These events can be registered in the usual way by calling
    :meth:`tangled.web.app.Application.add_subscriber`. There's also
    a convenience method for this:
    :meth:`tangled.web.app.Application.on_created`.

    Attributes: ``app``.

    """

    def __init__(self, app):
        self.app = app


class NewRequest:

    """Emitted when an application receives a new request.

    This is *not* emitted for static file requests.

    Attributes: ``app``, ``request``.

    """

    def __init__(self, app, request):
        self.app = app
        self.request = request


class ResourceFound:

    """Emitted when the resource is found for a request.

    Attributes: ``app``, ``request``, ``resource``.

    """

    def __init__(self, app, request, resource):
        self.app = app
        self.request = request
        self.resource = resource


class NewResponse:

    """Emitted when the response for a request is created.

    This is *not* emitted for static file requests.

    If there's in exception during request handling, this will *not* be
    emitted.

    Attributes: ``app``, ``request``, ``response``.

    """

    def __init__(self, app, request, response):
        self.app = app
        self.request = request
        self.response = response


class TemplateContextCreated:

    """Emitted when the context for a template is created.

    The template ``context`` is whatever data will passed to the
    template. E.g., for Mako, it's a dict.

    This is emitted just before the template is rendered. Its purpose
    is to allow additional data to be injected into the template
    context.

    Attributes: ``app``, ``request``, ``context``

    """

    def __init__(self, app, request, context):
        self.app = app
        self.request = request
        self.context = context


class Subscriber:

    # Internal; stores metadata along with subscriber function

    def __init__(self, event_type, func, priority=None, once=False, args=None):
        self.event_type = event_type
        self.func = func
        self.priority = sys.maxsize if priority is None else priority
        self.once = once
        self.args = args or {}  # Passed as kwargs to func

    @staticmethod
    def sorter(subscriber):
        return subscriber.priority
