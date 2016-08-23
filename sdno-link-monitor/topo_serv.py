#!/usr/bin/python
# -*- coding: utf-8 -*-
__author__ = 'liyiqun'

import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web
import threading
import tornado.gen
from topomodel import *
from jsonrpc import *
from test import *
from topofetch import topo_fetcher
from microsrvurl import *
from base_handler import *
from tornado_swagger import swagger
import datetime
from common import *
from flow_serv import flow_handler
import os
import os.path

swagger.docs()


topo_interval =  1000*1000
link_interval =  500*1000

class fetch_thread(threading.Thread):
    def __init__(self, app_obj):
        threading.Thread.__init__(self)
        self.app = app_obj
        self.fetcher = topo_fetcher()
        pass


    def set_link_list(self):

        if self.fetcher.vlink_modified == 0:
            return

        rpc = base_rpc(microsrv_linkstat_url)
        args = {}
        vls = []
        for l in self.fetcher.vlinks:
            vl = {}
            vl['uid'] = l['uid']
            e = {}
            ve = l['sequip']
            for k in ve:
                if k != 'ports':        # Don't let ports join the data, it's useless.
                    e[k] = ve[k]
            vl['equip'] =  e
            vl['ports'] = l['ports']
            vls.append(vl)
            pass

        args['vlinks'] = vls
        rpc.form_request('ms_link_set_links', args)
        r = rpc.do_sync_post()

        if r is not None:
            self.fetcher.vlink_modified = 0
        pass

    def set_equips(self):
        'Set the routers data to who requires them. e.g. the controller micro service'
        # Set equip data to ms_controller. Moved to sync_lsp of lsp_serv.py

        # Set equip and link data to ms_flow
        rpc = base_rpc(microsrv_flow_url)
        args = {}
        args['equips'] = self.fetcher.equips
        args['vlinks'] = self.fetcher.simple_vlinks
        rpc.form_request('ms_flow_set_topo', args)
        r = rpc.do_sync_post()

        pass


    def fetch_link_status(self):
        rpc = base_rpc(microsrv_linkstat_url)
        args = {}
        #args['uid'] = l['uid']
        rpc.form_request('ms_link_get_status', args)
        r = rpc.do_sync_post()
        if r is None:
            return

        r = r['utilization']
        for v in self.fetcher.vlinks:
            v['utilization'] = {}
        for u in r:
            pid = u['port_uid']
            if pid not in self.fetcher.vlink_map:
                continue;
            v = self.fetcher.vlink_map[pid]
            v['utilization'][pid] = float(u['utilization'])
            pass

        pass


    def form_equip_model(self):
        m = []
        for e in self.fetcher.equips:
            em = equipment()
            for k in e.keys():
                em.set_attrib(k, e[k])
            m.append(em.__dict__)
            pass

        if len(m) > 0:
            self.app.set_idle_equip(m)
            pass
        pass

    def form_vlink_model(self):
        m = []
        for v in self.fetcher.vlinks:
            vm = vlink()
            for k in v.keys():
                vm.set_attrib(k, v[k])
                pass

            vm.set_attrib('sequip', v['sequip']['uid'])
            vm.set_attrib('dequip', v['dequip']['uid'])

            # aggregate bandwidth usage
            total_bw = float(v['bandwidth'])
            total_usage = 0.0
            for p in v['ports']:
                pid = p['uid']
                if 'utilization' in v and  pid in v['utilization']:
                    total_usage +=  float(v['utilization'][pid])
                    pass
            vm.percentage = float(total_usage / total_bw)
            m.append(vm.__dict__)

        if len(m) > 0:
            self.app.set_idle_link(m)
        pass

    def run(self):

        last_topo_tm = 0
        last_link_tm = 0
        while(True):
            time.sleep(3)
            tm = int(time.time())
            if tm - last_topo_tm > topo_interval:
                self.fetcher.prepare()
                self.fetcher.fetch_equip()
                self.fetcher.fetch_port()
                self.fetcher.fetch_vlink()
                self.form_equip_model()
                self.fetch_link_status()
                self.form_vlink_model()
                self.set_link_list()
                self.set_equips()
                last_topo_tm = tm
                last_link_tm = tm
                self.app.switch_equip()
                self.app.switch_link()

            if tm - last_link_tm > link_interval:
                self.fetch_link_status()
                self.form_vlink_model()
                last_link_tm = tm
                self.app.switch_link()

            pass
        pass


class topo_handler(base_handler):
    def initialize(self):
        super(topo_handler, self).initialize()
        self.resp_func = {'topo_man_get_equip': self.get_equips, 'topo_man_get_vlinks':self.get_vlinks,
                          'topo_man_get_topo':self.get_topo}
        self.async_func = {'topo_man_update_equip':self.update_equip}
        self.log = 0
        pass


    def form_response(self, req):
        resp = {}
        resp['response'] = req['request']
        resp['ts'] = req['ts']
        resp['trans_id'] = req['trans_id']
        resp['err_code'] = 0
        resp['msg'] = ''
        return resp

    def get_equips(self,req):
        res = {}
        em = self.application.get_active_equip()
        res['routers'] = em
        return res

    def get_vlinks(self, req):
        res = {}
        vm = self.application.get_active_link()
        res['vlinks'] = vm
        return res

    def get_topo(self,req):
        em = self.application.get_active_equip()
        vm = self.application.get_active_link()
        res = {'node_list':em, 'links':vm}
        return res

    @tornado.gen.coroutine
    def update_equip(self,req):
        res = yield self.do_query(microsrv_topo_url, 'ms_topo_update_equip', req['args'])
        raise tornado.gen.Return(res)



    def get(self):
        self.write('TE+ topology service: provides get_topo interface.')
        pass

    @tornado.gen.coroutine
    def post(self):
        ctnt = self.request.body
        #self.write('You posted: ' + str(ctnt))
        try:
            req = json.loads(str(ctnt))
        except:
            self.write('Invalid Request')
            self.finish()

        resp = self.form_response(req)

        if req['request'] in self.async_func:
            res = yield self.async_func[req['request']](req)
            resp['result'] = res['result']
            self.write(json.dumps(resp))
            self.finish()
        else:
            res = None
            if 'request' in req and req['request'] in self.resp_func:
                res = self.resp_func[req['request']](req)
                resp['result'] = res
                if res is None:
                    resp['err_code'] = -2
                    resp['msg'] = 'Requested resource is not available now'
                    resp['result'] = {}
                print resp
                self.write(json.dumps(resp))
                self.finish()
            else:
                resp['err_code'] = -1
                resp['msg'] = 'Unrecongnized method'
                self.write(json.dumps(resp))
                self.finish()

        pass

    pass

class vlink_handler(base_handler):

    @tornado.gen.coroutine
    @swagger.operation(nickname='get_vlink')
    def get(self):
        """

            @rtype: {"vlinks": [{"ingress_node_uid": "1001","ingress_port_uid": "1001_0", "bandwidth": 1000.0, "util_ratio": 0.1072,
            "egress_port_uid": "1002_0", "egress_node_uid": "1002","uid": "v_0"}, {"ingress_port_uid": "1002_2",
            "bandwidth": 1000.0, "util_ratio": 25.98,  "egress_port_uid": "1000_3", "uid": "v_1"}]}
            <br /> <br />
            egress_node_uid: The universal id of egress node of the link. <br />
            egress_port_uid: The universal id of egress port of the link. <br />
            ingress_node_uid: The universal id of ingress node of the link. <br />
            ingress_port_uid: The universal id of ingress port of the link. <br />
            bandwidth: Maximum bandwidth of the link, in Mbps unit. <br />
            util_ratio: Current utilization ratio of the link, in percentage unit. i.e. 69.2 indicates 69.2% utilization.<br />


            @description: Get all vlinks and their bandwidth/utilization information
            @notes: GET /vlinks
        """
        res = {}
        vm = self.application.topo_app.get_active_link()
        sw_vm = self.application.map_link_attrib(vm)
        res['vlinks'] = sw_vm
        self.write(json.dumps(sw_vm))
        self.finish()
        pass




class topo_app(tornado.web.Application):
    def __init__(self):

        handlers = [
            (r'/', topo_handler),
            (r'/microsrv/topo', ms_topo_handler),
            (r'/microsrv/link_stat', ms_link_handler),
            (r'/microsrv/flow', ms_topo_handler),  # For testing
            (r'/microsrv/customer', ms_topo_handler),
            (r'/microsrv/tunnel', ms_topo_handler),
            (r'/microsrv/controller', ms_topo_handler)
        ]

        settings = {
            'template_path': 'templates',
            'static_path': 'static'
        }

        tornado.web.Application.__init__(self, handlers, **settings)

        self.equip = [None, None]
        self.cur_equip = 0

        self.link = [None, None]
        self.cur_link = 0

        fetcher = fetch_thread(self)
        fetcher.start()

        pass

    def switch_equip(self):
        self.cur_equip = 1 - self.cur_equip
        pass

    def switch_link(self):
        self.cur_link = 1 - self.cur_link
        pass

    def get_active_equip(self):
        return self.equip[self.cur_equip]

    def set_idle_equip(self, eq):
        self.equip[1 - self.cur_equip] = eq

    def get_active_link(self):
        return self.link[self.cur_link]

    def set_idle_link(self, lk):
        self.link[1 - self.cur_link] = lk

class flow_rest_handler(flow_handler):

    @tornado.web.asynchronous
    @swagger.operation(nickname='get_flow')
    def get(self, node_uid):
        """
            @param node_uid:
            @type node_uid: L{string}
            @in node_uid: path
            @required node_uid: True

            @rtype: map of {vsite_name:flow_information}
            <br /> <br />
            vsite_name: The name of a virtual site (collection of IP subnets) managed by vsite_mgr service <br />
            flow_information: A map contains IP flow details. Have flowing keys <br />
            &nbsp;&nbsp; lsps: An array of MPLS LSPs of the IP flow <br />
            &nbsp;&nbsp; flow_speed: Flow speed in bps unit. <br />


            @description: Get the sampled IP flow of a specific node.
            @notes: GET flows/node_uid:abc
        """
        req_body = self.flow_subreq({'args':{'equip_uid':node_uid}})
        http_req = tornado.httpclient.HTTPRequest(microsrv_flow_url ,method='POST', body = req_body)
        client = tornado.httpclient.AsyncHTTPClient()
        self.set_rest(1)
        client.fetch(http_req, callback = self.cb_fetch_flow)
        pass

class swagger_app(swagger.Application):
    def __init__(self, topo_app):
        settings = {
            'static_path': os.path.join(os.path.dirname(__file__), 'sdno-link-monitor.swagger')
        }

        handlers = [(r'/openoapi/sdno-link-monitor/v1/vlinks', vlink_handler),
                    (r'/openoapi/sdno-link-monitor/v1/flows/(.+)', flow_rest_handler),
                    (r'/openoapi/sdno-link-monitor/v1/(swagger.json)', tornado.web.StaticFileHandler, dict(path=settings['static_path']))
        ]

        super(swagger_app, self).__init__(handlers, **settings)
        self.topo_app = topo_app
        self.vlink_attrib_map = {'dequip':'ingress_node_uid', 'sequip':'egress_node_uid',
                                 'dport':'ingress_port_uid', 'sport':'egress_port_uid', 'bandwidth':'bandwidth',
                                 'percentage':'util_ratio'}
        tornado.ioloop.IOLoop.instance().add_timeout(
                        datetime.timedelta(milliseconds=500),
                        openo_register, 'link_flow_monitor', 'v1', '/openoapi/sdno-link_flow_monitor/v1',
                        '127.0.0.1', te_topo_rest_port )

        # For Test Only.
        tornado.ioloop.IOLoop.instance().add_timeout(
                        datetime.timedelta(milliseconds=1000),
                        openo_register, 'sdno-brs', 'v1', '/openoapi/sdno-brs/v1',
                        '127.0.0.1', 65500 )


    def map_link_attrib(self, vlinks):
        sw_vlinks = []
        for vl in vlinks:
            sw = {}
            for k in self.vlink_attrib_map:
                if k in vl:
                    sw[self.vlink_attrib_map[k]] = vl[k]
            sw_vlinks.append(sw)
        return sw_vlinks
        pass

if __name__ == '__main__':
    tornado.options.parse_command_line()
    app = topo_app()
    swag = swagger_app(app)    # For REST interface
    server = tornado.httpserver.HTTPServer(app)
    server_swag = tornado.httpserver.HTTPServer(swag)
    server.listen(32769)
    server_swag.listen(te_topo_rest_port)
    tornado.ioloop.IOLoop.instance().start()