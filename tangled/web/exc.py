import datetime
import html
import logging.handlers
import traceback

from webob.exc import HTTPInternalServerError


class ConfigurationError(Exception):

    """Exception used to indicate a configuration error."""


class DebugHTTPInternalServerError(HTTPInternalServerError):

    """For use in debug mode, mainly for showing tracebacks."""

    body_template = '<pre>{timestamp}\n\n{content}</pre>'

    def __init__(self, content, *args, **kwargs):
        now = datetime.datetime.now()
        content = html.escape(content)
        body_template = self.body_template.format(
            timestamp=now, content=content)
        super().__init__(body_template=body_template, *args, **kwargs)

        # HACK
        safe_substitue = self.body_template_obj.safe_substitute
        self.body_template_obj.substitute = safe_substitue


EXC_LOG_MESSAGE_TEMPLATE = """

{request.method} {request.url}
Requested by {request.remote_addr}
Referred by {request.referer}

Headers
=======

{headers}

Resource Config
===============

{resource_config}

Traceback
=========

"""


def get_exc_log_message(app, request, exc):
    if app.debug or request is None:
        message = format_exc(exc)
        if request is None:
            message += 'Request failed hard\n' + message
    else:
        if hasattr(request, 'resource'):
            try:
                resource_config = format_dict(request.resource_config.__dict__)
            except Exception as exc:
                resource_config = str(exc)
        else:
            resource_config = '[NONE]'
        message = EXC_LOG_MESSAGE_TEMPLATE.format(
            request=request,
            resource_config=resource_config,
            headers=format_dict(request.headers, exclude=('Cookie',)),
        )
    return message


def format_exc(exc, **kwargs):
    """Like the built in version but let's ``exc`` be specified.

    The built in version in ``traceback.format_exc`` always gets exc
    info from ``sys.exc_info()`` with no way to specify otherwise.

    """
    return ''.join(
        traceback.format_exception(exc.__class__, exc, exc.__traceback__),
        **kwargs)


def format_dict(dict_, include=(), exclude=()):
    out = []
    if include:
        keys = set(include)
    else:
        keys = set(dict_.keys())
        keys -= set(exclude)
    for k in sorted(keys):
        v = dict_.get(k, '[NOT PRESENT]')
        out.append('{}: {}'.format(k, v))
    out = '\n'.join(out)
    return out


class SMTPHandler(logging.handlers.SMTPHandler):

    def getSubject(self, record):
        return '{0.subject} {1}'.format(self, record.exc_info[1])
