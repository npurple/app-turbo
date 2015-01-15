# -*- coding:utf-8 -*-

from collections import namedtuple

import tornado.web
import tornado.escape

from pymongo import ASCENDING, DESCENDING
from bson.objectid import ObjectId

from turbo.util import escape as _es
import turbo.httputil as _ht 
from turbo.log import app_log
from turbo.core.exceptions import ResponseError

#TODO config 
from config import locale as LOCALE
#TODO lang setting 
from settings import (
    LANG as _LANG,
)


class BaseBaseHandler(tornado.web.RequestHandler):
    """
    config request parameter like this:
    _get_params = {
            'need':[
                ('skip', int),
                ('limit', int),
            ],
            'option':[
                ('jsoncallback', basestring, None),
            ]
        }

    """

    #override in subclass
    _required_params = [('skip', int, 0), ('limit', int, 0)] 
    _types = [ObjectId, None, basestring, int, float, list, file, bool]
    _data = None

    def initialize(self):
        # request context
        self.context = self.get_context()

        # app template path if exist must end with slash like user/
        self.template_path = ''

    def render(self, template_name, **kwargs):
        super(BaseBaseHandler, self).render('%s%s' % (self.template_path, template_name), context=self.context, **kwargs)

    def sort_by(self, sort):
        return {1: ASCENDING, -1: DESCENDING}.get(sort, ASCENDING)

    # request context
    def get_context(self):
        return {

        }

    def to_objectid(self, objid):
        return _es.to_objectid(objid)

    def to_int(self, value):
        return _es.to_int(value)

    def to_float(self, value):
        return _es.to_float(value)

    def to_bool(self, value):
        return _es.to_bool(value)

    def utf8(self, v):
        return tornado.escape.utf8(v)

    def static_url(self, path, include_host=None, v=None, **kwargs):
        is_debug = self.application.settings.get('debug', False)
        
        # In debug mode, load static files from localhost
        if is_debug: 
            return super(BaseBaseHandler, self).static_url(path, include_host, **kwargs)

        v = kwargs.get('v', '')

        return ('{host}/{path}?v={v}' if v else '{host}/{path}').format(host=_CDN['host'], path=path, v=v)


    def encode_http_params(self, **kw):
        """
        url parameter encode
        """
        return _ht.encode_http_params(**kw)

    def json_encode(self, data):
        return _es.json_encode(data)

    def json_decode(self, data):
        return _es.json_decode(data)

    # write output json
    def wo_json(self, data):
        callback = self.get_argument('jsoncallback', None)
        if callback:
            return self.write('%s(%s)' % (callback, self.json_encode(data)))

        self.write(self.json_encode(data))       

    # read in json
    def ri_json(self, data):
        return self.json_decode(data)

    def recur_to_str(self, v):
        return _es.recursive_to_str(v)

    @property
    def parameter(self):
        '''
        according to request method config to filter all request paremter
        if value is invalid then set None
        '''
        method = self.request.method.lower()
        arguments = self.request.arguments
        files = self.request.files

        rpd = {}  # request parameter dict

        def filter_parameter(key, tp, default=None):
            if tp not in self._types:
                raise ValueError("%s parameter expected types %s" % (key, self._types))

            if tp != file:
                if key not in arguments:
                    rpd[key] = default
                    return

                if tp in [ObjectId, int, float, bool]:
                    rpd[key] = getattr(self, 'to_%s' % getattr(tp, '__name__').lower())(self.get_argument(key))
                    return

                if tp == basestring:
                    rpd[key] = self.get_argument(key, strip=False)
                    return

                if tp == list:
                    rpd[key] = self.get_arguments(key)
                    return

            if tp == file:
                if key not in files:
                    rpd[key] = default
                    return

                rpd[key] = self.request.files[key]                
        
        for key, tp, default in self._required_params:
            filter_parameter(key, tp, default)
        
        params = getattr(self, '_%s_params' % method, None)
        if params is None:
            return rpd

        #need parameter
        for key, tp in params.get('need', []):
            if tp == list:
                filter_parameter(key, tp, [])
            else:
                filter_parameter(key, tp)

        #option parameter
        for key, tp, default in params.get('option', []):
            filter_parameter(key, tp, default)

        return rpd

    def get(self, *args, **kwargs):
        try:
            self.GET(*args, **kwargs)
        except ResponseError as e:
            resp = self.init_resp(e.code, e.msg)
        except Exception as e:
            app_log.exception(e)
            resp = self.init_resp(1)
        else:
            resp = self.init_resp()

        self.wo_resp(resp)

    def post(self, *args, **kwargs):
        try:
            self.POST(*args, **kwargs)
        except ResponseError as e:
            resp = self.init_resp(e.code, e.msg)
        except Exception as e:
            app_log.exception(e)
            resp = self.init_resp(1)
        else:
            resp = self.init_resp()

        self.wo_resp(resp)

    @staticmethod
    def init_resp(code=0, msg=None):
        resp = {
            'code': code,
            'msg': LOCALE.LANG_MESSAGE[_LANG].get(code) or msg,
            'res': {},
        }

        return resp

    def POST(self, *args, **kwargs):
        pass

    def GET(self, *args, **kwargs):
        pass

    def route(self, route, *args, **kwargs):
        getattr(self,  "do_%s"%route, lambda *args, **kwargs: None)(*args, **kwargs)

    def wo_resp(self, resp):
        if resp['code'] != 0:
            return self.wo_json(resp)

        if isinstance(self._data, dict):
            resp['res'].update(self._data)

        return self.wo_json(resp)


class BaseHandler(BaseBaseHandler):
    pass

def start():
    pass