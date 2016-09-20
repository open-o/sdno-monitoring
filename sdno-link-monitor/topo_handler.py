#!/usr/bin/python
# -*- coding: utf-8 -*-
#
#  Copyright (c) 2016, China Telecommunication Co., Ltd.
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


import tornado.web
import json
import time
from db_util import mysql_utils


class ms_topo_handler(tornado.web.RequestHandler):
    def initialize(self):
        super(ms_topo_handler, self).initialize()
        self.resp_func = {'ms_topo_get_equip': self.get_equips, 'ms_topo_get_ports':self.get_ports, \
                      'ms_topo_get_vlink': self.get_vlinks, 'ms_topo_update_equip':self.update_equip, \
                      'ms_topo_set_vlink_delay':self.set_vlink_delay}
        self.log = 0
        pass

    def form_response(self, req):
        resp = {}
        resp['response'] = req['request']
        #resp['ts'] = req['ts']
        resp['ts'] = time.strftime("%Y%m%d%H%M%S")
        resp['trans_id'] = req['trans_id']
        resp['err_code'] = 0
        resp['msg'] = ''
        self.set_header('Content-Type', 'application/json')
        return resp
    
    def post(self):
        ctnt = self.request.body
        if self.log == 1:
            print 'The request:'
            print  str(ctnt)

        req = json.loads(str(ctnt))
        resp = self.form_response(req)

        result = self.resp_func[req['request']](req['args'])
        resp['result'] = result

        if self.log == 1:
            print 'response:'
            print json.dumps(resp)
        self.write(json.dumps(resp))
        pass

    def update_equip(self, arg):

        if 'uid' in arg:
            uid = str(arg['uid'])
        if 'name' in arg:
            name = arg['name']

        sql_str = 'update t_router set t_router.name = \'%s\' where id=%s' % (name, uid)
        db = mysql_utils('topology')
        db.exec_sql(sql_str)
        db.commit()
        db.close()
        return {}

    def get_equips(self, arg):
        equips = {}
        rts = []
        
        sql_str = 'select * from t_router inner join t_site on t_router.site_id=t_site.id'
        db = mysql_utils('topology')
        results = db.exec_sql(sql_str)
        db.close()
        
        for result in results:
            one_rt = {}
            one_rt['uid'] = str(result[0])
            one_rt['name'] = result[2]
            #one_rt['model'] = result[2]
            one_rt['community'] = result[5]
            one_rt['vendor'] = result[6]
            #one_rt['pos'] = result[5]
            one_rt['x'] = result[7]
            one_rt['y'] = result[8]
            one_rt['ip_str'] = result[4]
            rts.append(one_rt)
            
        equips['routers'] = rts
        return equips

    def get_ports(self, arg):
        uid = arg['uid']
        port = {}
        ps = []

        sql_str = 'select * from t_port where t_port.router_id=%s' % uid
        print sql_str
        db = mysql_utils('topology')
        results = db.exec_sql(sql_str)
        db.close()
        
        for result in results:
            one_port = {}
            one_port['uid'] = str(result[0])
            one_port['type'] = result[2]
            one_port['mac'] = result[6]
            one_port['ip_str'] = result[8]
            one_port['if_index'] = result[9]
            one_port['if_name'] = result[4]
            ps.append(one_port)

        port['ports'] = ps
        return port
    
    def get_vlinks(self, arg):
        vl = {}
        vls = []

        sql_str = 'select * from t_link'
        db = mysql_utils('topology')
        results = db.exec_sql(sql_str)
        db.close()
        
        for result in results:
            v = {}
            v['uid'] = str(result[0])
            v['sport'] = str(result[1])
            v['dport'] = str(result[2])
            v['bandwidth'] = result[4]
            v['delay'] = result[6] if result[6] is not None and result[6] != '' else 0
            vls.append(v)

        vl['vlinks'] = vls
        return vl

    def set_vlink_delay(self, arg):
        ' args is {"vlinks":[{"uid":"xxx", "delay":123} ] }'
        dlys = arg['vlinks']

        db = mysql_utils('topology')
        for d in dlys:
            sqltxt = 'UPDATE t_link SET t_link.delay = %s WHERE t_link.id = %s' % (d['delay'], d['uid'])
            db.exec_sql(sqltxt)
        db.commit()
        db.close()
        return {}


