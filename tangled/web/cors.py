import logging


log = logging.getLogger(__name__)


def cors_handler(app, request, next_handler, ):
    """Handle CORS.

    If permissive CORS is not enabled, this does nothing.

    If the resource handles CORS itself by adding access control headers
    to the response, this does nothing.

    Otherwise...

    When the request method is OPTIONS, this will return a response that
    allows requests from the request's origin for any method and content
    type.

    When the request method is something other than OPTIONS, this will
    add a header to the response that allows the request.

    .. note:: This is mainly intended for use in development since it is
        INSECURE.

    """
    response = next_handler(app, request)
    permissive = app.get_setting('tangled.app.cors.permissive', False)

    if permissive:
        if not app.debug:
            log.warning('Permissive CORS is enabled; this is INSECURE')

        origin = request.headers.get('Origin')

        if origin and not has_cors_headers(response):
            if request.method == 'OPTIONS':
                if has_cors_headers(request):
                    response.headers.update({
                        'Access-Control-Allow-Origin': origin,
                        'Access-Control-Allow-Methods': '*',
                        'Access-Control-Allow-Headers': 'Content-Type',
                    })
            else:
                response.headers.update({
                    'Access-Control-Allow-Origin': origin,
                })

    return response


def has_cors_headers(obj):
    headers = obj.headers
    return any(name.startswith('Access-Control') for name in headers)
