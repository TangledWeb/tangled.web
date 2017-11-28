"""System handlers.

Requests are processed through a chain of handlers. This module contains
the "system" handlers. These are handlers that always run in a specific
order.

Most of the system handlers *always* run. They can't be turned off, but
you can swap in different implementations via settings. Take a look at
:file:`tangled/web/defaults.ini` to see how you would do this.

Some handlers are only enabled when certain settings are enabled or when
certain configuration takes place. For example, to enable CSRF
protection, the ``tangled.app.csrf.enabled`` setting needs to be set to
``True``. Another example: the static files handlers is only enabled
when at least one static directory has been mounted.

If an auth handler is enabled, it will run directly before any (other)
handlers added by the application developer.

All added handlers are called in the order they were added. The last
handler to run is always the :func:`main` handler; it calls into
application code (i.e., it calls a resource method to get data or
a response).

"""
import logging
import os
import pdb
import time
import traceback

from webob.exc import WSGIHTTPException, HTTPInternalServerError

from . import csrf
from .abcs import AMountedResourceTree
from .events import NewRequest, ResourceFound, NewResponse
from .exc import DebugHTTPInternalServerError
from .representations import Representation
from .response import Response


log = logging.getLogger(__name__)


def exc_handler(app, request, next_handler):
    try:
        return next_handler(app, request)
    except WSGIHTTPException as exc:
        response = exc
    except Exception as exc:
        app.log_exc(request, exc)
        if app.debug:
            if app.settings.get('debug.pdb', False):
                pdb.post_mortem(exc.__traceback__)
            return DebugHTTPInternalServerError(traceback.format_exc())
        else:
            response = HTTPInternalServerError()
    try:
        # TODO: Log errors for specified status codes? (e.g., 400)
        # TODO: Pull this out and make it configurable
        if response.status_code >= 400:
            # Display an error page if an error resource is configured
            error_resource = app.get_setting('error_resource')
            if error_resource:
                resource = error_resource(app, request)
                request.method = 'GET'
                request.resource = resource
                request.resource_method = 'GET'
                request.response = response
                del request.response_content_type
                del request.resource_config
                try:
                    return main(app, request, None)
                except WSGIHTTPException as exc:
                    app.log_exc(request, exc)
                    return exc
    except Exception as exc:
        app.log_exc(request, exc)

    # If there's an exception in the error resource (or there's no error
    # resource configured), the original exception response will be
    # returned, which is better than nothing.
    return response


def request_finished_handler(app, request, _):
    """Call request finished callbacks in exc handling context.

    This calls the request finished callbacks in the same exception
    handling context as the request. This way, if exceptions occur in
    finished callbacks, they can be logged and displayed as usual.

    .. note:: Finished callbacks are not called for static requests.

    """
    if not getattr(request, 'is_static', False):
        request._call_finished_callbacks(request.response)
    return request.response


def static_files(app, request, next_handler):
    prefix, rel_path = app._find_static_directory(request.path_info)
    if prefix is not None:
        request.is_static = True
        environ = request.environ.copy()
        environ['PATH_INFO'] = '/' + '/'.join(rel_path)
        static_request = app.make_request(environ)
        directory_app = app.get('static_directory', prefix)
        return directory_app(static_request)
    return next_handler(app, request)


def tweaker(app, request, next_handler):
    """Tweak the request based on special request parameters."""
    specials = {
        '$method': None,
        '$accept': None,
    }
    for k in request.params:
        if k in specials:
            specials[k] = request.params[k]
    for k in specials:
        if k in request.GET:
            del request.GET[k]
        if k in request.POST:
            del request.POST[k]

    if specials['$method']:
        method = specials['$method']
        tunneled_methods = app.get_setting('tunnel_over_post')

        if method == 'DELETE':
            # Changing request.method to DELETE makes request.POST
            # inaccessible.
            if csrf.KEY in request.POST and csrf.HEADER not in request.headers:
                request.headers[csrf.HEADER] = request.POST[csrf.KEY]

        if request.method == 'POST' and method in tunneled_methods:
            request.method = method
        elif app.debug:
            request.method = method
        else:
            request.abort(
                400, detail="Can't tunnel {} over POST".format(method))

    if specials['$accept']:
        request.accept = specials['$accept']
    elif app.settings['tangled.app.set_accept_from_ext']:
        root, ext = os.path.splitext(request.path_info)
        if ext:
            repr_type = app.get(Representation, ext.lstrip('.'))
            if repr_type is not None:
                request.accept = repr_type.content_type
                request.path_info = root

    return next_handler(app, request)


def notifier(app, request, next_handler):
    app.notify_subscribers(NewRequest, app, request)
    response = next_handler(app, request)
    app.notify_subscribers(NewResponse, app, request, response)
    return response


def resource_finder(app, request, next_handler):
    """Find resource for request.

    Sets ``request.resource`` and notifies :class:`ResourceFound`
    subscribers.

    If a resource isn't found, a 404 response is immediatley returned.
    If a resource is found but doesn't respond to the request's method,
    a ``405 Method Not Allowed`` response is returned.

    """
    tree = app.get_required(AMountedResourceTree)
    match = tree.find_for_request(request)

    if match is None:
        request.abort(404)

    mounted_resource = match.mounted_resource
    urlvars = match.urlvars

    if mounted_resource.add_slash and not request.path_info.endswith('/'):
        request.path_info += '/'
        request.abort(303, location=request.url)

    resource = mounted_resource.factory(
        app, request, mounted_resource.name, urlvars)
    method_name = mounted_resource.method_name or request.method

    if not hasattr(resource, method_name):
        request.abort(405)

    request.resource = resource
    request.resource_method = method_name
    app.notify_subscribers(ResourceFound, app, request, mounted_resource)
    return next_handler(app, request)


# csrf handler will be inserted here if enabled
# auth handler will be inserted here if enabled
# non-system handlers will be inserted here
# cors handler will be inserted here if enabled


def timer(app, request, next_handler):
    """Log time taken to handle a request."""
    start_time = time.time()
    response = next_handler(app, request)
    elapsed_time = (time.time() - start_time) * 1000
    log.debug('Request to {} took {:.2f}ms'.format(request.url, elapsed_time))
    return response


def main(app, request, _):
    """Get data from resource method and return response.

    If the resource method returns a response object (an instance of
    :class:`Response`), that response will be returned without further
    processing.

    If the status of ``request.response`` has been set to 3xx (either
    via @config or in the body of the resource method) AND the resource
    method returns no data, the response will will be returned as is
    without further processing.

    Otherwise, a representation will be generated based on the request's
    Accept header (unless a representation type has been set via
    @config, in which case that type will be used instead of doing
    a best match guess).

    If the representation returns a response object as its content, that
    response will be returned without further processing.

    Otherwise, `request.response` will be updated according to the
    representation type (the response's content_type, charset, and body
    are set from the representation).

    """
    method = getattr(request.resource, request.resource_method)
    data = method()

    if isinstance(data, Response):
        return data

    response = request.response

    if 300 <= response.status_code < 400 and data is None:
        return response

    info = request.resource_config
    log.debug(info)

    if info.type:
        differentiator = info.type
    else:
        differentiator = request.response_content_type
    repr_type = app.get_required(Representation, differentiator)

    kwargs = info.representation_args
    representation = repr_type(app, request, data, **kwargs)

    if isinstance(representation.content, Response):
        return representation.content

    response.content_type = representation.content_type
    response.charset = representation.encoding
    response.text = representation.content
    return response


class HandlerWrapper:

    # An internal class used for wrapping handler callables.

    def __init__(self, callable_, next_handler):
        self.callable_ = callable_
        self.next = next_handler

    def __call__(self, app, request):
        response = self.callable_(app, request, self.next)
        if response is None:
            raise ValueError('Handler returned None')
        return response
