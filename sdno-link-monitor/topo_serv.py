#!/usr/bin/python
# -*- coding: utf-8 -*-
#
#  Copyright 2016-2017 China Telecommunication Co., Ltd.
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

import copy
import datetime
import os
import os.path
import threading

import tornado.gen
import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web
from tornado.options import options
from tornado_swagger import swagger

from base_handler import *
from common import *
from flow_serv import flow_handler
from test import *
from topofetch import topo_fetcher
from topomodel import *

swagger.docs()


topo_interval =  60*60
link_interval =  10#500*1000

class fetch_thread(threading.Thread):
    def __init__(self, app_obj):
        threading.Thread.__init__(self)
        self.app = app_obj
        self.fetcher = topo_fetcher()
        pass


    def set_link_list(self):

        if self.fetcher.vlink_modified == 0:
            return

        rpc = base_rpc(microsrvurl_dict['microsrv_linkstat_url'])
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

    def set_topo(self):
        'Set the routers data to who requires them. e.g. the controller micro service'


        # Set equip and link data to ms_flow
        rpc = base_rpc(microsrvurl_dict['microsrv_flow_url'])
        args = {}
        args['equips'] = self.fetcher.equips
        print [x['ip_str'] for x in self.fetcher.equips]
        args['vlinks'] = self.fetcher.simple_vlinks
        rpc.form_request('ms_flow_set_topo', args)
        r = rpc.do_sync_post()

        rpc = base_rpc(microsrvurl_dict['microsrv_linkstat_url'])
        rpc.form_request('ms_link_set_links', args)
        rpc.do_sync_post()


        # Set to ms_controller
        rpc = base_rpc(microsrvurl_dict['microsrv_controller_url'])
        rpc.form_request('ms_controller_set_equips', args)
        rpc.do_sync_post()

        pass


    def fetch_link_status(self):
        rpc = base_rpc(microsrvurl_dict['microsrv_linkstat_url'])
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
            if 'port_uid' not in u:
                continue
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
            vm.set_attrib('sequip_name', v['sequip']['name'])
            vm.set_attrib('dequip_name', v['dequip']['name'])

            # aggregate bandwidth usage
            total_bw = float(v['bandwidth'])
            total_usage = 0.0
            for p in v['ports']:
                pid = p['uid']
                if 'utilization' in v and  pid in v['utilization']:
                    total_usage +=  float(v['utilization'][pid]) * total_bw
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
            time.sleep(2)
            tm = int(time.time())
            try:
                if tm - last_topo_tm > topo_interval:
                    self.fetcher.prepare()
                    self.fetcher.fetch_equip()
                    self.fetcher.fetch_port()
                    self.fetcher.fetch_vlink()
                    self.form_equip_model()
                    # self.set_link_list()
                    self.set_topo()
                    time.sleep(2)
                    self.fetch_link_status()
                    self.form_vlink_model()
                    last_topo_tm = tm
                    last_link_tm = tm
                    self.app.switch_equip()
                    self.app.switch_link()

                if tm - last_link_tm > link_interval:
                    self.fetch_link_status()
                    self.form_vlink_model()
                    last_link_tm = tm
                    self.app.switch_link()
            except Exception, e:
                print e
                traceback.print_exc()

            pass
        pass


class topo_handler(base_handler):
    def initialize(self):
        super(topo_handler, self).initialize()
        self.resp_func = {'topo_man_get_equip': self.get_equips, 'topo_man_get_vlinks':self.get_vlinks,
                          'topo_man_get_topo':self.get_topo}
        self.async_func = {'topo_man_update_equip':self.update_equip, 'topo_man_get_flow_by_equip':self.get_flow_by_equip,
                           'topo_man_set_vlink_delay':self.set_link_delay}
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
        equip = None
        if 'args' in req:
            req = req['args']
        if 'equip_uid' in req:
            equip = req['equip_uid']

        vm = self.application.get_active_link()
        if equip:
            vm = self.filter_vlink(vm, equip)
        res['vlinks'] = vm
        return res

    def get_topo(self,req):
        em = self.application.get_active_equip()
        vm = self.application.get_active_link()
        res = {'node_list':em, 'links':vm}
        return res

    def filter_vlink(self, vm, equip):
        ' Filter vlinks by equipment. output subset of vlinks that start from equip '
        filtered = []
        e = str(equip)
        for v in vm:
            if v['sequip'] == e:
                filtered.append(v)
                pass
            pass
        return filtered

    @tornado.gen.coroutine
    def update_equip(self,req):
        res = yield self.do_query(microsrvurl_dict['microsrv_topo_url'], 'ms_topo_update_equip', req['args'])
        raise tornado.gen.Return(res)

    @tornado.gen.coroutine
    def set_link_delay(self, req):
        res = yield self.do_query(microsrvurl_dict['microsrv_topo_url'], 'ms_topo_set_vlink_delay', req['args'])
        res = yield self.do_query(microsrvurl_dict['microsrv_controller_url'], 'ms_controller_set_vlink_delay', req['args'])

        raise tornado.gen.Return(res)


    @tornado.gen.coroutine
    def get_flow_by_equip(self, req):
        '''
            1. The req contains 'equip_uid' argument.  This func call ms_flow to get current flows in this equip.
            2. Current flows is a list of {src, dst, vlink_uid, bps}
            3. Aggregate all flows into {cust_uid, cust_name, bps, next_hop_uid, next_hop_name} and return the result
        '''
        final_resp = {'err_code':-1, 'result':{}}
        try:
            equip = req['args']['equip_uid']

            #Call ms_flow to get flow
            resp = yield self.do_query(microsrvurl_dict['microsrv_flow_url'], 'ms_flow_get_flow', {'equip_uid':equip})
            flows = resp['result']['flows']

            # Form src ip list and get customer of all flow.
            src_ips = {}
            for f in flows:
                src_ips[f['src']] = 0
            ip_list = [x for x in src_ips]

            resp = yield self.do_query(microsrvurl_dict['microsrv_cust_url'], 'ms_cust_get_customer_by_ip', {'ips':ip_list})
            custs = resp['result']

            #Aggregate data.  cust_flows is {cust_uid: {cust_name, hops:{next_hop_uid:{next_hop_name, bps} } }}
            cust_flows = {}
            equips = self.application.fetcher.fetcher.equip_map
            for f in flows:
                c = custs[f['src']] if f['src'] in custs else {'name':'Unknown', 'cust_uid':'-1'}
                cid = c['cust_uid']
                try:
                    next = str(f['next_hop_uid'])
                    if cid in cust_flows:
                        fs = cust_flows[cid]['hops']
                        if next in fs:
                            link = fs[next]
                            link['bps'] += f['bps']
                        else:
                            fs[next] =  {'next_hop_name':equips[next]['name'],
                                         'next_hop_uid':next,
                                                     'bps': f['bps']}
                    else:
                        hops = {next:{'next_hop_name':equips[next]['name'],
                                      'next_hop_uid':next, 'bps': f['bps']}}
                        cust_flows[cid] = {'cust_name':c['name'], 'hops':hops}
                except (KeyError,LookupError):
                    traceback.print_exc()
                    pass
                pass

            #form output flow list
            flow_list = []
            for c in cust_flows:
                f = {'cust_uid':c, 'cust_name':cust_flows[c]['cust_name']}
                hops = cust_flows[c]['hops']
                for h in hops:
                    fc = copy.copy(f)
                    fc['next_hop_name'] = hops[h]['next_hop_name']
                    fc['next_hop_uid'] = hops[h]['next_hop_uid']
                    fc['bps'] =  hops[h]['bps']
                    flow_list.append(fc)
                    pass
                pass

            # Sort the list.
            flow_list.sort(reverse=True, key=lambda x:x['bps'])

            final_resp['err_code'] = 0
            final_resp['result'] = {'flows':flow_list}

        except (LookupError, KeyError):
            traceback.print_exc()

        raise tornado.gen.Return(final_resp)


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
        self.write(json.dumps(res))
        self.finish()
        pass

@swagger.model()
class link(object):
    """
        @description:
            link modle
        @property links: link uid list
        @ptype links: C{list} of L{String}
    """
    def __init__(self, links):
        self.links = links

class workflow_topo_handler(base_handler):
    @tornado.gen.coroutine
    @swagger.operation(nickname='jam_links')
    def get(self, threshold):
        '''

        @param threshold:
        @type threshold: L{string}
        @in threshold: path
        @required threshold: True

        @rtype: L{link}
        @description: Get all jam link uids with given bandwidth utilization ratio threshold. A link with higher utilization ratio than this value will be regarded as jammed
        @notes: GET jam_links/{threshold}
        '''
        vm = self.application.get_active_link()
        uids = [v['uid'] for v in vm if float(v['percentage']) > float(threshold)]

        self.write(json.dumps({'links':uids}))
        self.finish()

        pass



class topo_app(swagger.Application):
    def __init__(self):

        handlers = [
            (r'/', topo_handler),
            (r'/jam_links/(.+)', workflow_topo_handler)
        ]

        settings = {
            'template_path': 'templates',
            'static_path': 'static'
        }

        # tornado.web.Application.__init__(self, handlers, **settings)
        super(topo_app, self).__init__(handlers, **settings)

        self.equip = [None, None]
        self.cur_equip = 0

        self.link = [None, None]
        self.cur_link = 0

        self.fetcher = fetch_thread(self)
        self.fetcher.start()
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
        # print 'Get Active Link:' + str(self.cur_link)
        return self.link[self.cur_link]

    def set_idle_link(self, lk):
        # print 'SET Link ' + str(1 - self.cur_link)
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
        http_req = tornado.httpclient.HTTPRequest(microsrvurl_dict['microsrv_flow_url'] ,method='POST', body = req_body)
        client = tornado.httpclient.AsyncHTTPClient()
        self.set_rest(1)
        client.fetch(http_req, callback = self.cb_fetch_flow)
        pass

def openo_related_service_query():
    #{"protocol": "REST", "url": "/openoapi/sdnovsitemgr/v1", "visualRange": 1, "version": "v1", "serviceName": "vsite_mgr", "nodes": [{"ip": "127.0.0.1", "port": 8600, "ttl": 0}]}
    # print('customer_url---:' + microsrv_cust_url)
    customer_server_resp = openo_query_service('vsite_mgr', 'v1')
    # microsrv_cust_url = 'http://127.0.0.1:33771/'
    if customer_server_resp is not None and 'nodes' in customer_server_resp:
        for item in customer_server_resp['nodes']:
            if 'ip' in item:
                microsrvurl_dict['microsrv_cust_url'] = 'http://' + item['ip'] + ':33771'
                break
    # print('customer_url+++:' + microsrv_cust_url)

    #{"driverInfo": {"protocol": "REST", "instanceID": "sdno-driver-ct-te_ID", "ip": "127.0.0.1", "driverName": "sdno-driver-ct-te", "services": [{"support_sys": [{"version": "v1", "type": "ct_te_driver"}], "service_url": "/openoapi/sdno-driver-ct-te/v1/"}], "port": 8670}}
    # print('microsrv_controller_url---:' + microsrv_controller_url)
    ms_controller_resp = openo_query_driver('sdno-driver-ct-te', 'sdno-driver-ct-te_ID', 'v1')
    # microsrv_controller_url = 'http://10.9.63.140:12727/'
    if ms_controller_resp is not None:
        for item in ms_controller_resp:
            if 'driverName' in item and 'sdno-driver-ct-te' == item['driverName']:
                if 'ip' in item:
                    microsrvurl_dict['microsrv_controller_url'] = 'http://' + item['ip'] + ':12727'
                    break
    # print('microsrv_controller_url+++:' + microsrv_controller_url)

    # microsrv_linkstat_url = 'http://219.141.189.72:10000/link/links'
    # microsrvurl_dict['microsrv_linkstat_url'] = 'http://127.0.0.1:10000/link/links'
    # print('microsrv_linkstat_url+++:' + microsrv_linkstat_url)
    # microsrv_flow_url = 'thtp://219.141.189.72:10001/flow'
    # microsrvurl_dict['microsrv_flow_url'] = 'http://127.0.0.1:10001/flow'
    # print('microsrv_flow_url+++:' + microsrv_flow_url)
    pass


class swagger_app(swagger.Application):
    def __init__(self, topo_app):
        settings = {
            'static_path': os.path.join(os.path.dirname(__file__), 'sdnomonitoring.swagger')
        }

        handlers = [(r'/openoapi/sdnomonitoring/v1/vlinks', vlink_handler),
                    (r'/openoapi/sdnomonitoring/v1/flows/(.+)', flow_rest_handler),
                    (r'/openoapi/sdnomonitoring/v1/(swagger.json)', tornado.web.StaticFileHandler, dict(path=settings['static_path']))
        ]

        super(swagger_app, self).__init__(handlers, **settings)
        self.topo_app = topo_app
        self.vlink_attrib_map = {'dequip':'ingress_node_uid', 'sequip':'egress_node_uid',
                                 'dport':'ingress_port_uid', 'sport':'egress_port_uid', 'bandwidth':'bandwidth',
                                 'percentage':'util_ratio'}
        tornado.ioloop.IOLoop.instance().add_timeout(
                        datetime.timedelta(milliseconds=500),
                        openo_register, 'link_flow_monitor', 'v1', '/openoapi/sdnomonitoring/v1',
                        microsrvurl_dict['te_topo_rest_host'], microsrvurl_dict['te_topo_rest_port'] )

        # For Test Only. topo_serv.py  need delete brs register after testing ok
        # tornado.ioloop.IOLoop.instance().add_timeout(
        #                 datetime.timedelta(milliseconds=1000),
        #                 openo_register, 'sdno-brs', 'v1', '/openoapi/sdno-brs/v1',
        #                 microsrvurl_dict['te_topo_rest_host'], microsrvurl_dict['te_topo_rest_port'] )

        tornado.ioloop.IOLoop.instance().add_timeout(
                        datetime.timedelta(milliseconds=1500), openo_related_service_query)


    def map_link_attrib(self, vlinks):
        sw_vlinks = []
        if vlinks is None:
            return sw_vlinks
        for vl in vlinks:
            sw = {}
            for k in self.vlink_attrib_map:
                if k in vl:
                    sw[self.vlink_attrib_map[k]] = vl[k]
            sw_vlinks.append(sw)
        return sw_vlinks
        pass


def strip_parse_from_argv():
    options.define("uniq", default="2837492392932769", help="service unique id")
    options.define("localurl", default=microsrvurl_dict['te_topo_rest_host'] + te_host_port_divider + str(microsrvurl_dict['te_topo_rest_port']), help="service host:port")
    options.define("msburl", default=microsrvurl_dict['te_msb_rest_host'] + te_host_port_divider + str(microsrvurl_dict['te_msb_rest_port']), help="micro service bus host:port")
    tornado.options.parse_command_line()
    microsrvurl_dict['te_topo_rest_host'] = options.localurl.split(':')[0]
    microsrvurl_dict['te_topo_rest_port'] = int(options.localurl.split(':')[1])
    microsrvurl_dict['openo_ms_url'] = te_protocol + options.msburl + openo_ms_url_prefix
    microsrvurl_dict['openo_dm_url'] = te_protocol + options.msburl + openo_dm_url_prefix
    microsrvurl_dict['openo_esr_url'] = te_protocol + options.msburl + openo_esr_url_prefix
    microsrvurl_dict['openo_brs_url'] = te_protocol + options.msburl + openo_brs_url_prefix

    pass

if __name__ == '__main__':
    strip_parse_from_argv()
    app = topo_app()
    swag = swagger_app(app)    # For REST interface
    server = tornado.httpserver.HTTPServer(app)
    server_swag = tornado.httpserver.HTTPServer(swag)
    server.listen(32769)
    server_swag.listen(microsrvurl_dict['te_topo_rest_port'])
    tornado.ioloop.IOLoop.instance().start()
