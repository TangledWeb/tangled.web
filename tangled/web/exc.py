import datetime
import html

from webob.exc import HTTPInternalServerError


class ConfigurationError(Exception):

    pass


class DebugHTTPInternalServerError(HTTPInternalServerError):

    """For use in debug mode, mainly for showing tracebacks."""

    body_template = '<pre>{timestamp}\n\n{content}</pre>'

    def __init__(self, content, *args, **kwargs):
        now = datetime.datetime.now()
        content = html.escape(content)
        body_template = self.body_template.format(
            timestamp=now, content=content)
        super().__init__(body_template=body_template, *args, **kwargs)
