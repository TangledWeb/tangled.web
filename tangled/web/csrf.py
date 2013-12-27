import binascii
import logging
from datetime import datetime, timedelta
from urllib.parse import urlparse

try:
    import Crypto
except ImportError:
    Crypto = None
else:
    from Crypto.Cipher import AES

from webob.exc import HTTPForbidden

from tangled.util import constant_time_compare, random_bytes, random_string

from .exc import ConfigurationError


log = logging.getLogger(__name__)


KEY = '_csrf_token'
HEADER = 'X-CSRFToken'
SAFE_METHODS = ('GET', 'HEAD', 'OPTIONS', 'TRACE')


def include(app):
    app.add_representation_info_field('*/*', 'csrf_exempt', False)
    app.add_request_attribute(csrf_token, decorator=property)
    app.add_request_attribute(encrypted_csrf_token, decorator=property)
    app.add_request_attribute(decrypt_csrf_token)
    app.add_request_attribute(expire_csrf_token)
    app.add_request_attribute(csrf_tag, decorator=property)

    if app.get_setting('csrf.encrypt_tokens') and Crypto is None:
        raise ConfigurationError(
            'PyCrypto needs to be installed to encrypt CSRF tokens')

    @app.on_created
    def on_created(event):
        if not event.app.get('session_factory'):
            raise ConfigurationError('CSRF protection requires sessions')


def csrf_token(request):
    if KEY not in request.session:
        request.session[KEY] = random_string(n=32)
        request.session.save()
    return request.session[KEY]


def encrypted_csrf_token(request):
    token = request.csrf_token
    if request.get_setting('csrf.encrypt_tokens'):
        key = random_bytes(n=16, as_hex=True)  # len(key) == 32
        token = request.csrf_token.encode('ascii')
        token = AES.new(key).encrypt(token)
        token = binascii.hexlify(token)
        token = b':'.join((key, token))
        token = token.decode('ascii')
    return token


def decrypt_csrf_token(request, token):
    if request.get_setting('csrf.encrypt_tokens'):
        token = token.encode('ascii')
        key, token = token.split(b':')
        token = binascii.unhexlify(token)
        token = AES.new(key).decrypt(token)
        token = token.decode('ascii')
    return token


def expire_csrf_token(request):
    if KEY in request.session:
        token = request.session.pop(KEY)
        request.session.save()
        log.debug('CSRF: expired token {}'.format(token))


def csrf_tag(request):
    tag = '<input type="hidden" name="{name}" value="{value}" />'
    tag = tag.format(name=KEY, value=request.encrypted_csrf_token)
    return tag


def csrf_handler(app, request, next_handler):
    if request.method not in SAFE_METHODS:
        if request.representation_info.csrf_exempt:
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
                cookie_token = request.decrypt_csrf_token(request.cookies[KEY])
                if not constant_time_compare(cookie_token, expected_token):
                    _forbid(
                        'cookie token mismatch: got {}; expected {}'
                        .format(cookie_token, expected_token))
            else:
                _forbid('token not present in cookies')

            if KEY in request.POST:
                post_token = request.decrypt_csrf_token(request.POST[KEY])
                if not constant_time_compare(post_token, expected_token):
                    _forbid(
                        'POST token mismatch: got {}; expected {}'
                        .format(post_token, expected_token))
            elif HEADER in request.headers:
                token = request.decrypt_csrf_token(
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
        token = request.encrypted_csrf_token
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



