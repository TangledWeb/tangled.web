import logging


log = logging.getLogger(__name__)


def cors_handler(app, request, next_handler, ):
    """Handle CORS pre-flight OPTIONS requests.

    If the request method is OPTIONS *and* the resource does not handle
    CORS pre-flight requests *and* permissive CORS is enabled, this will
    return a response that allows requests from any origin for any
    method and content type.

    When the request method is something other than OPTIONS, this has no
    effect.

    When the request method is OPTIONS and the resource handles CORS
    pre-flight requests, the resource is responsible for setting the
    appropriate CORS headers.

    If permissive CORS is not enabled, this will return a response with
    no access control headers, which will effectively disallow the
    original request.

    .. note:: This is mainly intended for use in development since it is
        INSECURE.

    """
    skip = (
        # Request can't be a CORS request if its method isn't OPTIONS
        (request.method != 'OPTIONS') or
        # Not a CORS request since there are no CORS headers
        (not any(h.startswith('Access-Control') for h in request.headers))
    )

    response = next_handler(app, request)

    if skip:
        return response

    permissive = app.get_setting('tangled.app.cors.permissive', False)

    if permissive:
        if not app.debug:
            log.warning('Permissive CORS is enabled; this is INSECURE')
        # Only add the permissive access control headers if the resource
        # doesn't add them itself.
        if not any(h.startswith('Access-Control') for h in response.headers):
            response.headers.update({
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': '*',
                'Access-Control-Allow-Headers': 'Content-Type',
            })

    return response
