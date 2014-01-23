import binascii
import logging
from datetime import datetime, timedelta
from urllib.parse import urlparse

from markupsafe import Markup
from webob.exc import HTTPForbidden

from tangled.util import constant_time_compare, random_string

from .const import SAFE_HTTP_METHODS
from .exc import ConfigurationError


log = logging.getLogger(__name__)


KEY = '_csrf_token'
HEADER = 'X-CSRFToken'
TOKEN_LENGTH = 32


def include(app):
    app.add_config_field('*/*', 'csrf_exempt', False)
    app.add_request_attribute(csrf_token)
    app.add_request_attribute(masked_csrf_token)
    app.add_request_attribute(unmask_csrf_token)
    app.add_request_attribute(expire_csrf_token)
    app.add_request_attribute(csrf_tag)

    @app.on_created
    def on_created(event):
        if not event.app.get('session_factory'):
            raise ConfigurationError('CSRF protection requires sessions')


@property
def csrf_token(request):
    if KEY not in request.session:
        request.session[KEY] = random_string(TOKEN_LENGTH)
        request.session.save()
    return request.session[KEY]


@property
def masked_csrf_token(request):
    pad = random_string(TOKEN_LENGTH)
    token = request.csrf_token
    # XOR the pad with the token by getting the int value of each char
    masked_token = (ord(pad[i]) ^ ord(token[i]) for i in range(TOKEN_LENGTH))
    # Encode the XORed ints as 2 * TOKEN_LENGTH hex characters
    masked_token = binascii.hexlify(bytes(masked_token))
    masked_token = masked_token.decode('ascii')
    return ''.join((pad, masked_token))


def unmask_csrf_token(request, masked_token):
    pad = masked_token[:TOKEN_LENGTH]
    masked_token = masked_token[TOKEN_LENGTH:].encode('ascii')
    # Convert hex characters back to TOKEN_LENGTH ints
    masked_token = binascii.unhexlify(masked_token)
    # XOR the pad with the ints to get back the ints representing the
    # characters in the original token
    token = (ord(pad[i]) ^ masked_token[i] for i in range(TOKEN_LENGTH))
    token = ''.join(chr(i) for i in token)
    return token


def expire_csrf_token(request):
    if KEY in request.session:
        token = request.session.pop(KEY)
        request.session.save()
        log.debug('CSRF: expired token {}'.format(token))


@property
def csrf_tag(request):
    tag = '<input type="hidden" name="{name}" value="{value}" />'
    tag = tag.format(name=KEY, value=request.masked_csrf_token)
    return Markup(tag)


def csrf_handler(app, request, next_handler):
    if request.method not in SAFE_HTTP_METHODS:
        if request.resource_config.csrf_exempt:
            log.debug('CSRF: exempt: {}'.format(request.url))
        else:
            if request.scheme == 'https':
                if request.referer is None:
                    _forbid('no REFERER for secure request')
                if not _same_origin(request.url, request.referer):
                    _forbid(
                        'origins differ: got {}; expected {}'
                        .format(request.referer, request.url))

            if KEY in request.session:
                expected_token = request.session[KEY]
            else:
                _forbid('token not present in session')

            if KEY in request.cookies:
                cookie_token = request.unmask_csrf_token(request.cookies[KEY])
                if not constant_time_compare(cookie_token, expected_token):
                    _forbid(
                        'cookie token mismatch: got {}; expected {}'
                        .format(cookie_token, expected_token))
            else:
                _forbid('token not present in cookies')

            if KEY in request.POST:
                post_token = request.unmask_csrf_token(request.POST[KEY])
                if not constant_time_compare(post_token, expected_token):
                    _forbid(
                        'POST token mismatch: got {}; expected {}'
                        .format(post_token, expected_token))
                del request.POST[KEY]
            elif HEADER in request.headers:
                token = request.unmask_csrf_token(
                    request.headers[HEADER])
                if not constant_time_compare(token, expected_token):
                    _forbid(
                        'header token mismatch: got {}; expected {}'
                        .format(token, expected_token))
            else:
                _forbid('no token present (in POST params or headers)')

            log.debug('CSRF: token validated')

    response = next_handler(app, request)

    if request.method in ('GET', 'HEAD'):
        one_year_from_now = datetime.utcnow() + timedelta(days=365)
        token = request.masked_csrf_token
        response.set_cookie(KEY, token, expires=one_year_from_now)
        log.debug('CSRF: cookie set')

    return response


def _forbid(reason):
    log.error('CSRF: {reason}'.format(reason=reason))
    raise HTTPForbidden()


def _same_origin(url_a, url_b):
    a = urlparse(url_a)
    b = urlparse(url_b)
    return (a.scheme, a.hostname, a.port) == (b.scheme, b.hostname, b.port)
