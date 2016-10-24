#!/usr/bin/env python
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


# All the object from database

import os
import sys

sys.path.append("../common")

os.environ["KLOG_DFCFG"] = os.environ.get("KLOG_DFCFG", "/tmp/snmp.dfcfg")
os.environ["KLOG_RTCFG"] = os.environ.get("KLOG_RTCFG", "/tmp/snmp.rtcfg")
os.environ["KLOG_MASK"] = os.environ.get("KLOG_MASK", "facewindFHNS")

from logtan import logtan
from singleton import AppSingleton, ClsSingleton

from utils import *
import confcenter
from xlogger import *
from bprint import *

from bottle import get, post, put, delete, run, request

from deferdo import DeferDo

import miethread

import json
import time

import pymongo
client = pymongo.MongoClient()
db = client.snmp

map_r__ip_str = {}
map_r__uid = {}

map_p__ip_str = {}
map_p__uid = {}


### ###########################################################
## Singleton and klog
#
############ singleton("/tmp/snmp.pid", "Singleton check failed: snmp already exists")
# setdebugable()

logtan.i("application launched")

klog.to_stdout()
klog.to_file("/tmp/snmp-%N%Y%R.log", size=10485760)


### ###########################################################
# Read default configuration
#

class MyConfCenter(confcenter.XConfCenter):

    def __init__(self):
        super(MyConfCenter, self).__init__(group="snmp", rw_cfg="./snmp.cfg")
        self.alias_init()

    def alias_init(self):
        self.alias("CMDPORT", "cmdport", 9020)
        self.alias("DEBUG", "debug", True)

conf = MyConfCenter()


### ###########################################################
# Everything is a NetObject
#
import helper

### ###########################################################
## Request and Response
#


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


### #####################################################################
# Globals
#

oid_static = {
    ".1.3.6.1.2.1.2.2.1.1": "ifIndex",
    ".1.3.6.1.2.1.2.2.1.2": "ifDescr",
    # ".1.3.6.1.2.1.2.2.1.3": "ifType",
    # ".1.3.6.1.2.1.2.2.1.5": "ifSpeed",
    ".1.3.6.1.2.1.31.1.1.1.15": "ifHighSpeed",
    ".1.3.6.1.2.1.2.2.1.6": "ifPhysAddress",
}

oid_runtime = {
    # ".1.3.6.1.2.1.2.2.1.10": "ifInOctets",
    # ".1.3.6.1.2.1.31.1.1.1.6": "ifHCInOctets",
    # ".1.3.6.1.2.1.2.2.1.11": "ifInUcastPkts",
    # ".2.3.6.1.2.1.2.2.1.12": "ifInNUcastPkts",
    # ".1.3.6.1.2.1.2.2.1.13": "ifInDiscards",
    # ".1.3.6.1.2.1.2.2.1.14": "ifInErrors",
    # ".1.3.6.1.2.1.2.2.1.15": "ifInUnknownProtos",
    # ".1.3.6.1.2.1.2.2.1.16": "ifOutOctets",
    ".1.3.6.1.2.1.31.1.1.1.10": "ifHCOutOctets",
    # ".1.3.6.1.2.1.2.2.1.17": "ifOutUcastPkts",
    # ".1.3.6.1.2.1.2.2.1.18": "ifOutNUcastPkts",
    # ".1.3.6.1.2.1.2.2.1.19": "ifOutDiscards",
    # ".1.3.6.1.2.1.2.2.1.20": "ifOutErrors",
    # ".1.3.6.1.2.1.2.2.1.21": "ifOutQLen",
}


class SnmpPortInfo():
    __metaclass__ = ClsSingleton

    def __init__(self, oid_static, oid_runtime):
        self.readyRouters = {}
        self.portInfos = {}

        # key = 'host:type:value'
        self.shortcuts = {}

        self.oid_static = oid_static
        self.oid_runtime = oid_runtime

    # Shortcut operation
    #
    # host : ip address of SNMP server
    # type : oid/name of the entry
    def sckey(self, host, type, value):
        return host + ":" + type + ":" + value

    def scget(self, host, type, value):
        key = self.sckey(host, type, value)
        #klog.d("key:%s" % key)
        return self.shortcuts.get(key)

    def scset(self, host, type, value, info):
        key = self.sckey(host, type, value)
        #klog.d("key:%s" % key)
        self.shortcuts[key] = info

    def splitline(self, line, oid):
        try:
            pfxlen = len(oid) + 1
            segs = line.split()
            if segs > 3 and segs[0].startswith(oid):
                name = segs[0][pfxlen:]
                type = segs[2][:-1]
                value = segs[3]
                return name, type, value
        except:
            pass
        return None, None, "What????"

    def snmpget(self, host, comm, vern, oid):
        cmd = ['snmpget', '-Oe', '-On', '-v', vern, '-c', comm, host, oid]
        lines = self.subcall(cmd)
        return self.splitline(lines[0], oid)

    def subcall(self, cmd):
        # print "CMD:", cmd
        try:
            return subprocess.check_output(cmd).replace("\r", "\n").split("\n")
        except:
            klog.e("CMD:%s\r\nBT:%s" % (cmd, traceback.format_exc()))
            return []

    def load_port_info(self, inf):
        oldrti = inf.get("rti", {})
        tmprti = {}

        newinf = {}
        tmprti["old"] = oldrti.get("new", {})
        tmprti["new"] = newinf

        bandwidth = int(inf.get("ifHighSpeed", 10000000)) * 1000000

        newinf["time"] = time.time()

        host = inf["__loopback__"]
        comm = inf["__snmp_comm__"]
        vern = inf["__snmp_vern__"]
        for oid_base, name in self.oid_runtime.items():
            oid = oid_base + "." + inf['ifIndex']
            _, _, value = self.snmpget(host, comm, vern, oid)
            newinf[name] = value

        try:
            delta_bytes = int(tmprti["new"]["ifHCOutOctets"]) - \
                int(tmprti["old"]["ifHCOutOctets"])
            if not delta_bytes:
                return

            delta_seconds = tmprti["new"]["time"] - tmprti["old"]["time"]

            tmprti["delta_bytes"] = delta_bytes
            tmprti["delta_seconds"] = delta_seconds or 1

            delta_bytes = (
                delta_bytes + 0xffffffffffffffff) % 0xffffffffffffffff
            tmprti["__delta_bytes___"] = delta_bytes
            tmprti["__delta_bytes_MiB__"] = delta_bytes / 1024 / 1024
            tmprti["__delta_bytes_GiB__"] = delta_bytes / 1024 / 1024 / 1024

            utilization = 800.0 * delta_bytes / delta_seconds / bandwidth

            tmprti["utilization"] = "{:.4f}".format(utilization)
        except:
            # traceback.print_exc()
            pass

        inf["rti"] = tmprti

    def load_static(self, host, comm, vern):
        '''Collector information according to router's information'''
        oid_ipAdEntIfIndex = ".1.3.6.1.2.1.4.20.1.2"
        oid_ifAdminStatusBase = ".1.3.6.1.2.1.2.2.1.7."

        snmpwalk = [
            'snmpwalk',
            '-Oe',
            '-On',
            '-v',
            vern,
            '-c',
            comm,
            host,
            oid_ipAdEntIfIndex]
        lines = self.subcall(snmpwalk)
        for line in lines:
            port_ipaddr, _, port_index = self.splitline(
                line, oid_ipAdEntIfIndex)
            if not port_ipaddr:
                continue

            oid_ifAdminStatus = oid_ifAdminStatusBase + port_index
            _, _, state = self.snmpget(host, comm, vern, oid_ifAdminStatus)

            if state != "1":
                print "Interface '%s' is down" % port_ipaddr
                continue

            #
            # Get PortInfo
            #

            # XXX: ifindex number maybe same across different routers
            hashkey = "%s#%s" % (host, port_index)
            inf = self.portInfos.get(hashkey)
            if not inf:
                inf = DotDict()
                self.portInfos[hashkey] = inf
                klog.d(
                    "New portInfo: host:%s, ipaddr:%s" %
                    (host, port_ipaddr))
            else:
                klog.d(
                    "Found portInfo: host:%s, ipaddr:%s" %
                    (host, port_ipaddr))

            inf["__loopback__"] = host
            inf["__snmp_comm__"] = comm
            inf["__snmp_vern__"] = vern
            inf["__ipaddr__"] = port_ipaddr

            for oid_base, name in self.oid_static.items():
                oid = oid_base + "." + port_index
                _, _, value = self.snmpget(host, comm, vern, oid)
                inf[name] = value

            #
            # Shortcuts
            #

            #
            self.save_ipaddr(port_ipaddr, inf)
            self.save_ifindex(host, inf["ifIndex"], inf)

            # Save to db
            db.devs.replace_one({"_id": hashkey}, inf, True)

            #
            # Mark that this router has collected the static information
            #
            hashkeys = self.readyRouters.get(host, set())
            hashkeys.add(hashkey)
            self.readyRouters[host] = hashkeys

    def fr_ipaddr(self, ipaddr):
        return self.scget("", "ipaddr", ipaddr)

    def save_ipaddr(self, ipaddr, inf):
        self.scset("", "ipaddr", ipaddr, inf)

    def fr_ifindex(self, host, ifindex):
        return self.scget(host, "ifindex", ifindex)

    def save_ifindex(self, host, ifindex, inf):
        self.scset(host, "ifindex", ifindex, inf)

    def load(self, host, comm, vern="2c"):
        if host not in self.readyRouters:
            self.load_static(host, comm, vern)

        klog.d("load runtime for: %s" % host)

        hashkeys = self.readyRouters.get(host, set()).copy()
        for hashkey in hashkeys:
            inf = self.portInfos.get(hashkey)
            self.load_port_info(inf)

    def load_each(self, dic):
        host = dic["ip_str"]
        comm = dic["community"]
        vern = "2c"
        self.load(host, comm, vern)

    def update(self):
        '''Scan mango and generate ifindex number and port ipaddr'''
        for dic in db.equips.find({}, {"_id": 0, "ip_str": 1, "community": 1}):
            DeferDo(self.load_each, dic)

spi = SnmpPortInfo(oid_static, oid_runtime)
spi.update()


class Collector(miethread.MieThread):
    '''Thread pool to get data from snmp or netconf'''
    __metaclass__ = ClsSingleton

    def __init__(self, name="SnmpCollector"):
        klog.d("INTO Collector")
        miethread.MieThread.__init__(self, name=name)
        self.start()

    def act(self):
        '''Fetch and save to db'''
        spi.update()
        return 10

snmpCollector = Collector()


@post("/link/links")
def docmd_ms_link_links():
    calldic = idic()

    klog.d(varfmt(calldic, "calldic"))

    request = calldic["request"]

    if request == "ms_link_set_links":
        return ms_link_set_links(calldic)

    if request == "ms_link_get_status":
        return ms_link_get_status(calldic)

    return "Bad request '%s'" % request

'''
db.equips:
    ...

db.ports:
    Infomation from snmp scan and uid etc
    XXX: vport?
'''


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

    db.equips.drop()
    db.vlinks.drop()
    db.ports.drop()

    equips = calldic["args"].get("equips", [])
    vlinks = calldic["args"].get("vlinks", [])

    for r in equips:
        ports = r["ports"]
        del r["ports"]

        r["_id"] = r["ip_str"]
        db.equips.replace_one({"_id": r["_id"]}, r, True)

        for p in ports:
            p["_id"] = p["ip_str"]
            p["router"] = r["ip_str"]
            db.ports.replace_one({"_id": p["_id"]}, p, True)

    for l in vlinks:
        port = db.ports.find_one({"uid": l["sport"]})
        if port:
            port["bandwidth"] = l.get("bandwidth")
            db.ports.replace_one({"_id": port["_id"]}, port, True)

    respdic = odic(calldic)
    res = json.dumps(respdic)

    update_map()
    spi.update()
    return res


def update_map():
    global map_r__ip_str, map_r__uid, map_p__ip_str, map_p__uid
    map_r__ip_str = {}
    map_r__uid = {}
    map_p__ip_str = {}
    map_p__uid = {}

    for r in db.equips.find({}):
        map_r__ip_str[r["ip_str"]] = r
        map_r__uid[r["uid"]] = r

    for p in db.ports.find({}):
        map_p__ip_str[p["ip_str"]] = p
        map_p__uid[p["uid"]] = p


def get_utilization():
    utilization = []

    for k, v in spi.portInfos.items():
        ipaddr = v.get("__ipaddr__")
        dbport = db.ports.find_one({"ip_str": ipaddr})
        if dbport:
            try:
                obj = DotDict()

                obj.port_uid = dbport.get("uid")
                obj.if_name = dbport.get("if_name")
                obj.utilization = v["rti"].get("utilization", 0)

                obj["__obj_mm__"] = v
                obj["__obj_db__"] = dbport

                utilization.append(obj)
            except:
                pass
        else:
            klog.e("Notfound: port.ip_str == %s" % ipaddr)

    return utilization


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
                },

                {
                    "s_port_uid": "1000_2",
                    "d_port_uid": "1000_2",
                    "utilization": 259.8
                }
            ]
        },
        "trans_id": 1464244693,
        "ts": "20160526143813"
    }

    '''

    calldic = calldic or idic()
    varprt(calldic)
    respdic = odic(calldic)

    respdic.result.utilization = get_utilization()

    return json.dumps(respdic)


### #####################################################################
# mcon etc
#
from roar import CallManager, CmdServer_Socket
import roarcmds

callman = CallManager()
cmdserv = CmdServer_Socket(callman, conf.CMDPORT)
cmdserv.start()

callman.addcmd(roarcmds.docmd_dr, "dr")
callman.addcmd(roarcmds.docmd_stat, "stat")

roarcmds.ConfCommands(conf, callman)


@callman.deccmd()
def status(cmdctx, calldic):
    opt = calldic.get_opt("l")
    limit = opt[-1] if opt else "1000000"

    arg = calldic.get_args()
    pat = arg[0] if arg else None

    res = get_utilization()
    if pat:
        lis = []
        for r in res:
            if str(r).find(pat) >= 0:
                lis.append(r)
    else:
        lis = res

    lis.sort(key=lambda x: float(x.get("utilization", 0)), reverse=True)

    return lis[:int(limit)]


@callman.deccmd()
def map_r__ip_str(cmdctx, calldic):
    return map_r__ip_str


@callman.deccmd()
def map_r__uid(cmdctx, calldic):
    return map_r__uid


@callman.deccmd()
def map_p__ip_str(cmdctx, calldic):
    return map_p__ip_str


@callman.deccmd()
def map_p__uid(cmdctx, calldic):
    return map_p__uid


@callman.deccmd()
def portInfos(cmdctx, calldic):
    return spi.portInfos


@callman.deccmd()
def restart(cmdctx, calldic):
    def seeya(cookie):
        time.sleep(1)
        os._exit(0)

    DeferDo(seeya)
    return "Bye"



def strip_uniq_from_argv():
    '''The --uniq is used to identify a process.

    a.py --uniq=2837492392994857 argm argn ... argz
    ps aux | grep "--uniq=2837492392994857" | awk '{print $2}' | xargs kill -9
    '''

    for a in sys.argv:
        if a.startswith("--uniq="):
            sys.argv.remove(a)


if __name__ == "__main__":
    strip_uniq_from_argv()

    update_map()
    run(server='paste', host='0.0.0.0', port=10000, debug=True)

