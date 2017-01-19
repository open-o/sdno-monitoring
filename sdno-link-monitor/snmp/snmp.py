#!/usr/bin/env python
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


import os
import sys
import subprocess
import traceback
import time
import re

sys.path.append("../mie")

from confcenter import XConfCenter
import miethread

from logtan import logtan_mongodb as logtan
from singleton import AppSingleton, ClsSingleton

from bprint import varprt, varfmt
from dotdict import DotDict
from xlogger import klog
from deferdo import DeferDo
from maptan import MapTan
from kstat import kstat, kstatone
from logmon import KLogMon
from snmpoper import SnmpOper as sop, oid as soid

import pymongo
client = pymongo.MongoClient()
db = client.snmp



### ###########################################################
## Singleton and klog
#
AppSingleton("/tmp/snmp.pid", "Singleton check failed: snmp already exists")

### ###########################################################
## Read default configuration
#

alias = (
        ("CMDPORT", "cmdport", 9020),
        ("DEBUG", "debug", True),
        )

conf = XConfCenter(group="snmp", rw_cfg="./snmp.cfg", alias=alias)
KLogMon(conf)


### #####################################################################
## Globals
#

oid_static = set([
    "ifIndex",
    "ifDescr",
    "ifType",
    "ifSpeed",
    "ifHighSpeed",
    "ifPhysAddress",
    "ifAdminStatus",
    "ifOperStatus",
    ])

oid_runtime = set([
    # "ifInOctets",
    # "ifHCInOctets",
    # "ifInUcastPkts",
    # "ifInNUcastPkts",
    # "ifInDiscards",
    # "ifInErrors",
    # "ifInUnknownProtos",
    # "ifOutOctets",
    "ifHCOutOctets",
    # "ifOutUcastPkts",
    # "ifOutNUcastPkts",
    # "ifOutDiscards",
    # "ifOutErrors",
    # "ifOutQLen",
])


### #####################################################################
## Used to fast access port via some critiria
#

# ipaddr <=> port
g_port_fr_ipaddr = MapTan(lambda *a: str(a[0]))

# loopback + ifIndex <=> port
g_port_fr_ifindex = MapTan(lambda *a: "%s@%s" % (a[1], a[0]))

# ipaddr <=> setport
g_setport_fr_ip = MapTan(lambda *a: str(a[0]))

# portUid <=> setport
g_setport_fr_uid = MapTan(lambda *a: str(a[0]))

# All routes
# {loopback: DotDict}
g_routers = {}


### #####################################################################
## Router
#
class Router(DotDict):
    #__metaclass__ = ClsSingleton

    def __init__(self, oid_static, oid_runtime, host, comm="ctbri", vern="2c", **kwargs):
        # kwargs: other fields of a router
        self.ports = {}

        self.oid = {"static": oid_static, "runtime": oid_runtime}

        self.host = host        # ip_str
        self.comm = comm        # community
        self.vern = vern        # version

        for k, v in kwargs.items():
            self[k] = v

    def load_runtime(self, inf):
        oids = self.oid.get("runtime", [])
        if not oids:
            return

        oldrti = inf.get("rti", DotDict())
        tmprti = DotDict()

        newinf = DotDict()
        tmprti["old"] = oldrti.get("new", DotDict())
        tmprti["new"] = newinf

        newinf["time"] = time.time()

        host = inf["__loopback__"]
        comm = inf["__snmp_comm__"]
        vern = inf["__snmp_vern__"]

        for name in oids:
            oid = soid.get(name) + "." + str(inf.ifIndex)
            try:
                _, _, value = sop.get(host, comm, vern, oid)
                newinf[name] = value
            except:
                traceback.print_exc()
                pass

        inf["rti"] = tmprti

    def load_static(self):
        '''Collector information according to router's information'''

        host, comm, vern = self.host, self.comm, self.vern

        lines = sop.walk(host, comm, vern, soid.ipAdEntIfIndex)
        for line in lines:
            port_ipaddr, _, port_index = sop.splitline(
                line, soid.ipAdEntIfIndex)
            if not port_ipaddr:
                continue

            # XXX: ifindex number maybe same across different routers
            inf = DotDict()
            self.ports[port_index] = inf

            inf["__loopback__"] = host
            inf["__snmp_comm__"] = comm
            inf["__snmp_vern__"] = vern
            inf["__ipaddr__"] = port_ipaddr

            oids = self.oid.get("static", [])
            for name in oids:
                oid = soid.get(name) + "." + str(port_index)
                try:
                    _, _, value = sop.get(host, comm, vern, oid)
                    inf[name] = value
                except:
                    traceback.print_exc()
                    pass

    def load(self):
        if not self.ports:
            klog.d("load static for: %s" % self.host)
            self.load_static()

        klog.d("load runtime for: %s" % self.host)
        for p in self.ports.values():
            self.load_runtime(p)

def load_router(equip):
    loopback = equip.get("ip_str")
    if not loopback:
        return

    r = Router(oid_static, oid_runtime, loopback, **equip)
    r.load()
    g_routers[loopback] = r

    for p in r.ports.values():
        g_port_fr_ipaddr.set(p, p.__ipaddr__)
        g_port_fr_ifindex.set(p, p.__loopback__, p.ifIndex)


# Scan all given routers
def load_routers(ips):
    global g_routers, g_port_fr_ipaddr, g_port_fr_ifindex

    g_routers = {}
    g_port_fr_ipaddr.clr()
    g_port_fr_ifindex.clr()

    for loopback in ips:
        d = DotDict()
        d.ip_str = loopback
        d.community = "ctbri"
        d.vern = "2c"
        d.name = "Equip@%s" % loopback
        d.uid = loopback
        d.vendor = "FIXME"

        load_router(d)


class Collector(miethread.MieThread):
    '''Thread pool to get data from snmp or netconf'''
    __metaclass__ = ClsSingleton

    def load_each(self, r):
        klog.d("Loading ...:", r.host)
        r.load()

    def update(self):
        '''Scan mango and generate ifindex number and port ipaddr'''
        for r in g_routers.values():
            DeferDo(self.load_each, r)

    def __init__(self, name="SnmpCollector"):
        klog.d("INTO Collector")
        miethread.MieThread.__init__(self, name=name)
        self.start()

    def act(self):
        '''Fetch and save to db'''

        klog.d("Collector, acting...")
        self.update()
        return 10

snmpCollector = Collector()



### ###########################################################
## Bottle: Request and Response
#

from bottle import get, post, put, run, request
import json

def idic():
    try:
        payload = request.body.read() or "{}"
        dic = json.JSONDecoder().decode(payload)
        dic = DotDict(**dic)
        return dic
    except:
        traceback.print_exc()
        return DotDict()


def odic(indic):
    odic = DotDict()

    odic.response = indic.request
    odic.trans_id = indic.trans_id
    odic.ts = time.strftime("%Y%m%d%H%M%S")

    odic.result = DotDict()

    odic.err_code = 0
    odic.msg = None

    return odic

# request_name <> func
g_cmdmap = DotDict()

def cmd_default(calldic=None):
    return "Bad request '%s'" % calldic.request
g_cmdmap.default = cmd_default

@post("/link/links")
def docmd_ms_link_links():
    calldic = idic()
    klog.d(varfmt(calldic, "calldic"))
    return g_cmdmap.get(calldic.request, "default")(calldic)

def ms_link_set_links(calldic=None):
    '''
    {
        "args": {
            "equips": [
                {
                    "community": "ctbri",
                    "ip_str": "11.11.11.11",
                    "name": "PE11_ALU",
                    "ports": [
                        {
                            "capacity": 1000,
                            "if_index": 2,
                            "if_name": "ALU   1/1/1",
                            "ip_str": "10.0.111.11",
                            "mac": "00-00-0A-00-6F-0B",
                            "type": 1,
                            "uid": "3"
                        },
                        {
                            "capacity": 1000,
                            "if_index": 3,
                            "if_name": "ALU   1/1/2",
                            "ip_str": "10.0.114.11",
                            "mac": "00-00-0A-00-72-0B",
                            "type": 0,
                            "uid": "13"
                            "__associated_port__": 3
                        }
                    ],
                    "uid": "2",
                    "vendor": "ALU",
                    "x": 115.0,
                    "y": 150.0
                },
            ],
        },
        "request": "ms_flow_set_topo",
    }
    '''
    calldic = calldic or idic()

    db.ports.drop()

    db.equips.drop()
    equips = calldic["args"].get("equips", [])
    for r in equips:
        ports = r["ports"]
        del r["ports"]

        DeferDo(load_router, r)

        r["_id"] = r["ip_str"]
        db.equips.replace_one({"_id": r["_id"]}, dict(r), True)

        for p in ports:
            p["_id"] = "%s@%s" % (p["ip_str"], r["ip_str"])
            p["router"] = r["ip_str"]
            db.ports.replace_one({"_id": p["_id"]}, dict(p), True)

            g_setport_fr_ip.set(p, p.ip_str)
            g_setport_fr_uid.set(p, p.uid)

    db.vlinks.drop()
    vlinks = calldic["args"].get("vlinks", [])
    for l in vlinks:
        port = db.ports.find_one({"uid": l["sport"]})
        if port:
            port["bandwidth"] = l.get("bandwidth")
            db.ports.replace_one({"_id": port["_id"]}, dict(port), True)

    respdic = odic(calldic)
    res = json.dumps(respdic)

    # TODO: Save new information to db
    snmpCollector.wakeup()
    return res

g_cmdmap.ms_link_set_links = ms_link_set_links

class SizeConv():
    @classmethod
    def tos(cls, size, unit=None, fp=False, pre=0):
        '''toStr: 1234213412 => 1234213B => 1234KB => 1MB'''

        if unit in 'kK':
            size = float(size) / 1024
        elif unit in 'mM':
            size = float(size) / 1024 / 1024
        elif unit in 'gG':
            size = float(size) / 1024 / 1024 / 1024
        elif unit in 'tT':
            size = float(size) / 1024 / 1024 / 1024 / 1024
        elif unit in 'pP':
            size = float(size) / 1024 / 1024 / 1024 / 1024 / 1024
        else:
            size = float(size)

        if fp:
            pat = "{:.%df}" % pre if pre else "{:f}"
            return pat.format(size)
        else:
            return int(size)


    @classmethod
    def frs(cls, size, fp=False):
        '''frStr: 34712384K => 34712384*1024'''

        if not size:
            return 0

        size = size.strip()

        if size[-1] in 'kK':
            size = float(size[:-1]) * 1024
        elif size[-1] in 'mM':
            size = float(size[:-1]) * 1024 * 1024
        elif size[-1] in 'gG':
            size = float(size[:-1]) * 1024 * 1024 * 1024
        elif size[-1] in 'tT':
            size = float(size[:-1]) * 1024 * 1024 * 1024 * 1024
        elif size[-1] in 'pP':
            size = float(size[:-1]) * 1024 * 1024 * 1024 * 1024 * 1024
        else:
            size = float(size)

        return size if fp else int(size)

sc = SizeConv()


conf.alias("NETUSE_DEBUG", "netuse/debug", True)
def netusage(asc=True):
    out = []
    for r in g_routers.values():
        for p in r.ports.values():
            klog.d(varfmt(p, "NetUsage", True))
            try:

                d = DotDict()

                ipaddr = p.get("__ipaddr__")
                dbport = db.ports.find_one({"ip_str": ipaddr})
                if not dbport:
                    klog.e("Port (%s) not found" % ipaddr)
                    if not conf.NETUSE_DEBUG:
                        continue
                else:
                    d.port_uid = dbport.get("uid")
                    d.if_name = dbport.get("if_name")

                    d["__obj_db__"] = dbport


                new = int(p.rti.new.ifHCOutOctets)
                old = int(p.rti.old.ifHCOutOctets)

                diff_bytes = new - old

                diff_seconds = p.rti.new.time - p.rti.old.time
                bw_in_bytes = int(p.ifHighSpeed) * 1000000 / 8

                d.utilization = 100.0 * diff_bytes / diff_seconds / bw_in_bytes

                d.__diff_seconds = diff_seconds

                b = sc.tos(diff_bytes, "b", False, 3)
                k = sc.tos(diff_bytes, "k", True, 3)
                m = sc.tos(diff_bytes, "m", True, 3)
                g = sc.tos(diff_bytes, "g", True, 3)
                text = "%sB or %sK or %sM or %sG Bytes" % (b, k, m, g)
                d.__diff_size = text

                b = sc.tos(bw_in_bytes, "b", False, 3)
                k = sc.tos(bw_in_bytes, "k", True, 3)
                m = sc.tos(bw_in_bytes, "m", True, 3)
                g = sc.tos(bw_in_bytes, "g", True, 3)
                text = "%sB or %sK or %sM or %sG Bytes" % (b, k, m, g)
                d.__bandwidth = text

                d.ip = p.__ipaddr__
                d.loopback = p.__loopback__

                setp = g_setport_fr_ip.get(d.ip)
                if setp:
                    d.port_uid = setp.uid
                    d.if_name = setp.if_name

                out.append(d)
            except:
                continue

    mul = 10000000000 if asc else -10000000000
    return sorted(out, lambda x, y: int(mul * (x.utilization - y.utilization)))


def ms_link_get_status(calldic=None):
    '''
    The request:
    {
        "args": {},
        "request": "ms_link_get_status",
        "trans_id": 1464244693,
        "ts": "20160526143813"
    }
    response:
    {
        "err_code": 0,
        "msg": "Demo response",
        "response": "ms_link_get_status",
        "result": {
            "utilization": [
                {
                    "port_uid": "1000_0",
                    "utilization": 107.2
                },
                {
                    "port_uid": "1000_2",
                    "utilization": 259.8
                }
            ]
        },
        "trans_id": 1464244693,
        "ts": "20160526143813"
    }
    '''

    calldic = calldic or idic()
    respdic = odic(calldic)

    respdic.result.utilization = netusage(False)

    return json.dumps(respdic)

g_cmdmap.ms_link_get_status = ms_link_get_status


def ms_link_set_tunnel(calldic=None):
    '''
    The request:
    {
        "args": {
            "tunnels": [
                {
                    "bandwidth": 1000,
                    "from_router_name": "",
                    "from_router_uid": "router0",
                    "name": "Microhard_0",
                    "path": [
                        {},
                        {}
                    ],
                    "to_router_name": "",
                    "to_router_uid": "router4",
                    "uid": "lsp_0",
                    "user_data": "xxx"
                }
            ]
        },
        "request": "ms_link_set_tunnel",
        "trans_id": 1464244693,
        "ts": "20160526143813"
    }
    response:
    {
    }
    '''

    calldic = calldic or idic()
    respdic = odic(calldic)
    return json.dumps(respdic)

g_cmdmap.ms_link_set_tunnel = ms_link_set_tunnel


def ms_link_get_tunnel_bw(calldic=None):
    '''
    The request:
    {
        "args": {},
        "request": "ms_link_get_tunnel_bw",
        "trans_id": 1464244693,
        "ts": "20160526143813"
    }
    response:
    {
        "err_code": 0,
        "msg": "Demo response",
        "response": "ms_link_get_tunnel_bw",
        "result": {
            "tunnel_bw": [
                {
                    "cur_bw": "yyy",
                    "tunnel_uid": "xxx"
                }
            ]
        },
        "trans_id": 1464244693,
        "ts": "20160526143813"
    }
    '''
    calldic = calldic or idic()
    respdic = odic(calldic)
    return json.dumps(respdic)

g_cmdmap.ms_link_get_tunnel_bw = ms_link_get_tunnel_bw

### #####################################################################
## mcon etc
#
from roar.roar import CallManager, CmdServer_Socket
from roar import roarcmds

callman = CallManager(name="SNMP")
cmdserv = CmdServer_Socket(callman, conf.CMDPORT)
cmdserv.start()

roarcmds.ExtCommands(callman, conf)


@callman.deccmd()
def pl(cmdctx, calldic):
    '''Port List

    .opt -i byIpAddr
    .opt -l byLoopback
    .opt -as byAdminState
    Query by state, 1 for up, others for down
    .opt -os byOperState
    Query by state, 1 for up, others for down
    .opt --s pat :.*
    Use re to filter out the wanted port.

    TODO: should and --include and --exclude option.
    TODO: should and --include and --exclude option.
    TODO: should and --include and --exclude option.
    TODO: should and --include and --exclude option.
    '''
    ports = []
    args = calldic.get_args() or []

    pat = calldic.nth_opt("s", 0, ".*")
    pat = re.compile(pat)

    if calldic.get_opt("i"):
        field = "__ipaddr__"
    elif calldic.get_opt("l"):
        field = "__loopback__"
    elif calldic.get_opt("as"):
        field = "ifAdminStatus"
    elif calldic.get_opt("os"):
        field = "ifOperStatus"
    else:
        field = "__ipaddr__"

    for r in g_routers.values():
        for p in r.ports.values():
            if not args or str(p[field]) in args:
                ports.append(p)

    res = [p for p in ports if pat.search(str(p))]
    return res


@callman.deccmd()
def rl(cmdctx, calldic):
    '''Routers List

    .opt --s searchpat :.*
    '''
    lis = []
    args = calldic.get_args() or []

    pat = calldic.nth_opt("s", 0, ".*")
    pat = re.compile(pat)

    for r in g_routers.values():
        if not args or r.host in args:
            lis.append(r)

    res = [r for r in lis if pat.search(str(r))]
    return res


@callman.deccmd()
def rload(cmdctx, calldic):
    '''Routers load'''
    for r in g_routers.values():
        r.load()
    return "OK"


@callman.deccmd()
def util(cmdctx, calldic):
    '''Bandwidth usage

    Show Bandwidth usage.
    a. aaaaaaaaaaaa
    b. aaaaaaaaaaaa

    .opt --s searchPat :.*
    .arg count




    How many count should be returned.
    How many count should be returned.


    How many count should be returned.
    How many count should be returned.



    .arg fake
    Show this part

    .arg fake2




    '''
    cnt = calldic.nth_arg(0) or 1000000
    cnt = int(cnt)

    pat = calldic.nth_opt("s", 0, ".*")
    pat = re.compile(pat)

    utils = netusage(False)

    res = [i for i in utils if pat.search(str(i))]
    return res[:cnt]

@callman.deccmd()
def iplist(cmdctx, calldic):
    '''Show all ip address return by scan operation'''
    ips = []
    for r in g_routers.values():
        ips.extend([p["__ipaddr__"] for p in r.ports.values()])
    return sorted(ips, lambda x,y: int(x.split(".")[0]) - int(y.split(".")[0]))


if __name__ == "__main__":
    # map(lambda x: klog.d("#" * x), range(10, 100, 10))
    ips = sys.argv[1:]
    if ips:
        load_routers(ips)
        topo_scan(g_routers)
    else:
        ips = []
        for dic in db.equips.find({}, {"_id": 0, "ip_str": 1, "community": 1}):
            ips.append(dic.get("ip_str"))
        load_routers(ips)

    run(server='paste', host='0.0.0.0', port=10000, debug=True)

