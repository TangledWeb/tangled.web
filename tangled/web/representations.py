import datetime
import html
import json
from abc import ABCMeta, abstractmethod
from collections import Mapping

from .abcs import AResponse
from .events import TemplateContextCreated


class Representation(metaclass=ABCMeta):

    encoding = 'utf-8'
    quality = 0.5

    def __init__(self, app, request, data, encoding=None):
        self.app = app
        self.request = request
        self.data = data
        if encoding is not None:
            self.encoding = encoding
        if not isinstance(data, self.data_type):
            raise TypeError(
                'Got {}; expected {}'
                .format(data.__class__, self.data_type))

    @property
    @abstractmethod
    def key(self):
        raise NotImplementedError

    @property
    @abstractmethod
    def data_type(self):
        raise NotImplementedError

    @property
    @abstractmethod
    def content_type(self):
        raise NotImplementedError

    @property
    @abstractmethod
    def content(self):
        raise NotImplementedError


class NoContentRepresentation(Representation):

    key = 'no_content'
    data_type = None.__class__
    content_type = ''

    @property
    def content(self):
        return self.app.get_required(AResponse)(status=204)


class StringRepresentation(Representation):

    key = 'string'
    data_type = object
    content_type = 'text/plain'

    @property
    def content(self):
        return str(self.data)


class HTMLRepresentation(Representation):

    key = 'html'
    content_type = 'text/html'
    data_type = object

    @property
    def content(self):
        return html.escape(str(self.data))


class JSONRepresentation(Representation):

    key = 'json'
    content_type = 'application/json'
    data_type = Mapping

    @property
    def content(self):
        # TODO: Prepend 'while(1);' (if set)?
        encoder_cls = self.app.get_setting('representation.json.encoder')
        default = self.app.get_setting('representation.json.encoder.default')
        if encoder_cls is not None or default is not None:
            return json.dumps(self.data, cls=encoder_cls, default=default)
        else:
            return json.dumps(self.data, default=self.default)

    @staticmethod
    def default(o):
        if hasattr(o, '__json_data__'):
            return o.__json_data__()
        elif isinstance(o, (datetime.date, datetime.datetime)):
            return o.timestamp()
        raise TypeError('{!r} is not JSON serializable'.format(o))


class TemplateMixin:

    data_type = Mapping

    def template_context(self, **extra):
        context = dict(
            app=self.app,
            settings=self.app.settings,
            request=self.request,
            response=self.request.response,
            resource=self.request.resource,
        )
        context.update(self.data)
        context.update(extra)
        self.app.notify_subscribers(
            TemplateContextCreated, self.app, self.request, context)
        return context
