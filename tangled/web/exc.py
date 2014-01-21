import datetime
import html

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
