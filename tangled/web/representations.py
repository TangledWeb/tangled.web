import html
import json
from abc import ABCMeta, abstractmethod
from collections import Mapping

from .abcs import AResponse
from .events import TemplateContextCreated


class Representation(metaclass=ABCMeta):

    encoding = 'utf-8'

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
    data_type = str
    content_type = 'text/plain'

    @property
    def content(self):
        return str(self.data)


class HTMLRepresentation(Representation):

    key = 'html'
    content_type = 'text/html'
    data_type = str

    @property
    def content(self):
        return html.escape(self.data)


class JSONRepresentation(Representation):

    key = 'json'
    content_type = 'application/json'
    data_type = Mapping

    @property
    def content(self):
        # TODO: Prepend 'while(1);' (if set)?
        return json.dumps(self.data)


class TemplateMixin:

    data_type = Mapping

    def template_context(self, **extra):
        context = dict(
            app=self.app,
            settings=self.app.settings,
            request=self.request,
            response=self.request.response,
        )
        context.update(self.data)
        context.update(extra)
        self.app.notify_subscribers(
            TemplateContextCreated, self.app, self.request, context)
        return context
