#!/usr/bin/python
# -*- coding: utf-8 -*-
#
#  Copyright 2016 China Telecommunication Co., Ltd.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#

__author__ = 'liyiqun'
import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web
import tornado.httpclient
import tornado.gen
import json
import threading
import traceback

from topofetch import *
from jsonrpc import *
from microsrvurl import *
from test import *
from tornado_swagger import swagger
from common import *
import datetime

swagger.docs()

flow_equip_interval = int(3600 * 1000)


class fetch_thread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.fetcher = topo_fetcher()
        self.last_fetch = 0
        pass

    def set_equips(self):
        rpc = base_rpc(microsrvurl_dict['microsrv_flow_url'])
        args = {}
        args['equips'] = self.fetcher.equips
        rpc.form_request('ms_flow_set_equips', args)
        res = rpc.do_sync_post()
        pass


    def run(self):
        while (True):
            tm = int(time.time())
            if tm - self.last_fetch > flow_equip_interval:
                self.fetcher.fetch_equip()
                self.fetcher.fetch_port()
                self.set_equips()
                self.last_fetch = tm
            time.sleep(1)
            pass
        pass


class flow_handler(tornado.web.RequestHandler):
    def initialize(self):
        super(flow_handler, self).initialize()
        self.subreq_func = {'flow_man_get_flow': self.flow_subreq}
        self.callback_func = {'flow_man_get_flow': self.cb_fetch_flow}
        self.req = None
        self.log = 0
        self.rest = 0
        pass

    def set_rest(self, r):
        self.rest = 1


    def form_response(self, req):
        resp = {}
        resp['response'] = req['request']
        resp['ts'] = req['ts']
        resp['trans_id'] = req['trans_id']
        resp['err_code'] = 0
        resp['msg'] = ''
        return resp

    def flow_subreq(self, req):
        if 'args' not in req:
            return None

        # No need to specify url. we do not use the base_rpc for real request.
        rpc = base_rpc('')
        rpc.form_request('ms_flow_get_flow', req['args'])
        return json.dumps(rpc.request_body)


    def get(self):
        self.write('TE+ customer flow service.')
        pass

    def accum_flow(self,flow):
        ' Accumulate flows of same customer'
        orig = flow
        accu = {}
        for f in orig:
            if f['customer'] in accu:
                fobj = accu[f['customer']]
                if 'bps' in fobj:
                    fobj['bps'] = int(fobj['bps']) + int(f['bps'])
                else:
                    fobj['bps'] = int(f['bps'])
            else:
                #create new object
                fobj = {}
                fobj['bps'] = int(f['bps'])
                fobj['lsps'] = {}
                accu[f['customer']] = fobj

            # lsps = fobj['lsps']
            # if 'lsp_uid' in f:
            #     uid = f['lsp_uid']
            #
            #     if uid in lsps:
            #         lsp = lsps[uid]
            #         lsp['bps'] = int(lsp['bps']) + int(f['bps'])
            #     else:
            #         lsp = {}
            #         lsp['lsp_uid'] = uid
            #         lsp['lsp_name'] = f['lsp_name']
            #         lsp['bps'] = int(f['bps'])
            #         lsps[uid] = lsp

        flow = accu
        return flow

    def rest_result(self,flow):

        return json.dumps(flow)

    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def cb_fetch_flow(self, flow_resp):
        try:
            resp = {}
            if self.req:
                resp = self.form_response(self.req)
            flow = json.loads(flow_resp.body)
            if 'result' not in flow:
                if self.rest == 0:
                    resp['err_code'] = -1
                    resp['result'] = {}
                    self.write(json.dumps(resp))
                else:
                    self.write('{}')
                self.finish()

            flow = flow['result']
            if 'flows' in flow:
                flow = flow['flows']
            else:
                flow = []

            # mapping flow ip into customer name
            # No need to specify url. we do not use the base_rpc for real request.
            rpc = base_rpc('')
            args = {}
            ipl = {}

            for one_flow in flow:
                if 'src' in one_flow:
                    ipl[one_flow['src']] = 0
                pass

            args['ips'] = ipl.keys()
            rpc.form_request('ms_cust_get_customer_by_ip', args)
            req_body = json.dumps(rpc.request_body)

            http_req = tornado.httpclient.HTTPRequest(microsrvurl_dict['microsrv_cust_url'] ,method='POST', body = req_body)
            client = tornado.httpclient.AsyncHTTPClient()
            cust_resp = yield tornado.gen.Task(client.fetch, http_req)

            #check response
            cust_resp = json.loads(cust_resp.body)
            if 'result' not in cust_resp:
                self.write('{}')
                self.finish()

            ip_cust_map = cust_resp['result']
            for one_flow in flow:
                if 'src' not in one_flow:
                    continue
                sip = one_flow['src']
                if sip in ip_cust_map:
                    a_cust = ip_cust_map[sip]
                    one_flow['customer'] = a_cust['name']
                else:
                    one_flow['customer'] = 'Unknown'

            #On-return, flow will be a map of (customer:flow_details)
            flow = self.accum_flow(flow)

            # Get flow's LSP information
            # args = {'cust_uids':flow.keys()}
            # rpc.form_request('ms_tunnel_get_lsp_by_cust', args)
            # req_body = json.dumps(rpc.request_body)
            #
            # http_req = tornado.httpclient.HTTPRequest(microsrv_tunnel_url ,method='POST', body = req_body)
            # client = tornado.httpclient.AsyncHTTPClient()
            # lsp_resp = yield tornado.gen.Task(client.fetch, http_req)
            #
            # try:
            #     lsp_resp = json.loads(lsp_resp.body)
            #     if 'err_code' in lsp_resp and int(lsp_resp['err_code']) == 0 \
            #             and 'result' in lsp_resp :
            #         cust_lsp = lsp_resp['result']
            #         for cust in cust_lsp:
            #             if cust in flow:
            #                 flow[cust]['lsps'] = cust_lsp[cust]
            # except:
            #     pass

            if self.rest == 0:
                resp['err_code'] = 0
                resp['result'] = flow
                self.write(json.dumps(resp))
                if self.log == 1:
                    print json.dumps(resp)
            else:
                self.write(self.rest_result(flow))
            self.finish()

        except Exception, data:
            print 'Fetch flow from micro service error'
            print str(Exception) + ':' + str(data)
            traceback.print_exc()
            self.write(json.dumps(resp))
            self.finish()

        raise tornado.gen.Return()

        pass

    @tornado.web.asynchronous
    def post(self):
        try:
            ctnt = self.request.body
            # self.write('You posted: ' + str(ctnt))
            req = json.loads(str(ctnt))
            self.req = req
            resp = self.form_response(req)
            res = None
            if 'request' not in req or req['request'] not in self.subreq_func:
                resp['err_code'] = -1
                resp['msg'] = 'Unrecognised method'
                self.write(json.dumps(resp))
                self.finish()
                return


            req_body = self.subreq_func[req['request']](req)
            http_req = tornado.httpclient.HTTPRequest(microsrvurl_dict['microsrv_flow_url'] ,method='POST', body = req_body)
            client = tornado.httpclient.AsyncHTTPClient()
            client.fetch(http_req, callback = self.callback_func[req['request']])
        except Exception, data:
            print str(Exception) + str(data)
            self.write('Internal Server Error')
            traceback.print_exc()

    pass

class flow_app(tornado.web.Application):
    def __init__(self):
        handlers = [
            (r'/', flow_handler),
        ]

        settings = {
            'template_path': 'templates',
            'static_path': 'static'
        }

        tornado.web.Application.__init__(self, handlers, **settings)

        # We don't need the topo fetcher now. The topo service will set the topo to ms_flow instead.
        # fet = fetch_thread()
        # fet.start()
        pass

# Useless at this moment
class swagger_app(swagger.Application):
    def __init__(self, topo_app):
        handlers = [(r'/openoapi/sdno-link_flow_monitor/v1/flows/(.+)', flow_handler)]

        super(swagger_app, self).__init__(handlers)
        self.topo_app = topo_app
        self.flow_attrib_map = {}


if __name__ == '__main__':
    tornado.options.parse_command_line()
    app = flow_app()
    server = tornado.httpserver.HTTPServer(app)
    server.listen(32770)
    # swag = swagger_app(app)    # For REST interface
    # swag_server = tornado.httpserver.HTTPServer(swag)
    # server.listen(te_flow_rest_port)
    tornado.ioloop.IOLoop.instance().start()