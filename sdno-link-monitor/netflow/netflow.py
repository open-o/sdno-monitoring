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
import shutil
import json
import time
import traceback
import subprocess
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
from snmpoper import SnmpOper as sop

import nfmon


### ###########################################################
## Singleton and klog
#
AppSingleton("/tmp/netflow.pid", "Singleton check failed: netflow already exists")

nfp_recs = kstatone("nfp.recs")
nfp_recs_ok = kstatone("nfp.recs.ok")
nfp_recs_ng = kstatone("nfp.recs.ng")

lc_loops = kstatone("lc.loops")
lc_logs = kstatone("lc.logs")


# Journal for Netflow
logtan.cfg(db="jnetflow")

import functools
jni = functools.partial(logtan.i, mod="Netflow")
jnw = functools.partial(logtan.w, mod="Netflow")
jne = functools.partial(logtan.e, mod="Netflow")
jnf = functools.partial(logtan.f, mod="Netflow")

### ###########################################################
## Read default configuration
#

alias = (
        ("CMDPORT", "cmdport", 9021),

        ("SAMPLE_RATE", "sample/rate", 1000),

        # Bottle web service
        ("BOTTLE_PORT", "bottle/port", 10001),
        ("BOTTLE_DEBUG", "bottle/debug", False),

        ("LOG_CLEANER_TTL", "logcleaner/ttl", 60*10),

        # age/max: Max time between to same log items
        # age/skip: Drop too old record for get status
        ("DB_LOG_AGE_MAX", "db/log/age/max", 300),
        ("DB_LOG_AGE_SKIP", "db/log/age/skip", 180),
        )

conf = XConfCenter(group="netflow", rw_cfg="./netflow.cfg", alias=alias)
KLogMon(conf)

import pymongo
client = pymongo.MongoClient()
db = client.netflow

db.logs.create_index([("_id", pymongo.ASCENDING),
                      ("loopback", pymongo.ASCENDING),
                      ("nLoopback", pymongo.ASCENDING),
                      ("port.output", pymongo.ASCENDING),
                      ("port.nexthop", pymongo.ASCENDING)])
db.vlinks.create_index([("_id", pymongo.ASCENDING),
                        ("sportip", pymongo.ASCENDING),
                        ("dportip", pymongo.ASCENDING)])


'''
db.devs - Actually, this is the physical network port
    * ifIndex - Same as equips.ports.if_index
    * ifPhysAddress - Same as equips.ports.mac
    * router - router's ip this port belong to.

db.logs
    *

db.equips
    * ip_str - This should be management port, used by snmp
    * community - used by SNMP
    * uid

db.port
    * if_index
    * ip_str
    * mac
    * type
    * uid

db.links
    * sport - db.port.uid
    * dport - db.port.uid
    * uid

=== Fast Map ===
    *
'''

oid_ipAdEntIfIndex = ".1.3.6.1.2.1.4.20.1.2"
oid_ifAdminStatusBase = ".1.3.6.1.2.1.2.2.1.7."
oid_ifOperStatusBase = ".1.3.6.1.2.1.2.2.1.8."

oid_static = {
    ".1.3.6.1.2.1.2.2.1.1": "ifIndex",
    # ".1.3.6.1.2.1.2.2.1.2": "ifDescr",
    # ".1.3.6.1.2.1.2.2.1.3": "ifType",
    # ".1.3.6.1.2.1.2.2.1.5": "ifSpeed",
    # ".1.3.6.1.2.1.31.1.1.1.15": "ifHighSpeed",
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
    # ".1.3.6.1.2.1.31.1.1.1.10": "ifHCOutOctets",
    # ".1.3.6.1.2.1.2.2.1.17": "ifOutUcastPkts",
    # ".1.3.6.1.2.1.2.2.1.18": "ifOutNUcastPkts",
    # ".1.3.6.1.2.1.2.2.1.19": "ifOutDiscards",
    # ".1.3.6.1.2.1.2.2.1.20": "ifOutErrors",
    # ".1.3.6.1.2.1.2.2.1.21": "ifOutQLen",
}


### ###########################################################
## SNMP
#
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
        return host + ":" + str(type) + ":" + str(value)

    def scget(self, host, type, value):
        key = self.sckey(host, type, value)
        return self.shortcuts.get(key)

    def scset(self, host, type, value, info):
        key = self.sckey(host, type, value)
        self.shortcuts[key] = info

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
            _, _, value = sop.get(host, comm, vern, oid)
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

        downports = []

        lines = sop.walk(host, comm, vern, oid_ipAdEntIfIndex)
        for line in lines:
            port_ipaddr, _, port_index = sop.splitline(
                line, oid_ipAdEntIfIndex)
            if not port_ipaddr:
                continue

            oid_ifAdminStatus = oid_ifAdminStatusBase + str(port_index)
            _, _, state = sop.get(host, comm, vern, oid_ifAdminStatus)

            if state != 1:
                downports.append(port_ipaddr)
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
                oid = oid_base + "." + str(port_index)
                _, _, value = sop.get(host, comm, vern, oid)
                inf[name] = value

            #
            # Shortcuts
            #

            #
            self.save_ipaddr(port_ipaddr, inf)
            self.save_ifindex(host, inf["ifIndex"], inf)

            # Save to db
            db.devs.replace_one({"_id": hashkey}, dict(inf), True)

            #
            # Mark that this router has collected the static information
            #
            hashkeys = self.readyRouters.get(host, set())
            hashkeys.add(hashkey)
            self.readyRouters[host] = hashkeys

        if downports:
            klog.e("(%s) DownPorts: %s" % (host, downports))

    def fr_ipaddr(self, ipaddr):
        return self.scget("", "ipaddr", ipaddr)

    def save_ipaddr(self, ipaddr, inf):
        self.scset("", "ipaddr", ipaddr, inf)

    def fr_ifindex(self, host, ifindex):
        return self.scget(host, "ifindex", ifindex)

    def save_ifindex(self, host, ifindex, inf):
        self.scset(host, "ifindex", ifindex, inf)

    def unload(self, host):
        hashkeys = self.readyRouters.get(host)
        if not hashkeys:
            klog.e("unload router %s failed, it not loaded yet" % host)
            return

        klog.d("unload router: %s" % host)

        for hashkey in hashkeys:
            try:
                del self.portInfos[hashkey]
            except:
                pass

        try:
            del self.readyRouters[host]
        except:
            pass

    def load(self, host, comm, vern="2c"):
        if host not in self.readyRouters:
            klog.d("load static for: %s" % host)
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
            klog.d(varfmt(dic))
            DeferDo(self.load_each, dic)

spi = SnmpPortInfo(oid_static, oid_runtime)


### ###########################################################
## LogCleaner - Cleanup old log items
#
class LogCleaner(miethread.MieThread):
    __metaclass__ = ClsSingleton

    def __init__(self, keeptime=1200):
        self.keeptime = keeptime
        miethread.MieThread.__init__(self)
        self.start()

    def setkeeptime(self, seconds):
        self.keeptime = seconds
        self.wakeup()

    def act(self):
        lc_loops.inc()

        ctime = time.time() - self.keeptime
        query = {"time.log": {"$lt": ctime}}
        res = db.logs.delete_many(query)
        klog.d("%s" % varfmt(query))
        klog.d("%d deleted." % res.deleted_count)

        lc_logs.inc(res.deleted_count)

        return self.keeptime * 9 / 10

lc = LogCleaner(conf.LOG_CLEANER_TTL)



### ###########################################################
## NFRecProcessor - Server to process NF packages
#
class NFRecProcessor():
    @staticmethod
    def rec2dic(routerip, rec):
        try:
            src_addr = "%d.%d.%d.%d" % (rec.src_addr_a, rec.src_addr_b, rec.src_addr_c, rec.src_addr_d)
            nexthop = "%d.%d.%d.%d" % (rec.nexthop_a, rec.nexthop_b, rec.nexthop_c, rec.nexthop_d)
            dst_addr = "%d.%d.%d.%d" % (rec.dst_addr_a, rec.dst_addr_b, rec.dst_addr_c, rec.dst_addr_d)

            in_if = rec.in_if
            out_if = rec.out_if

            packets = rec.packets
            octets = rec.octets

            first = rec.first
            last = rec.last

            src_port = rec.src_port
            dst_port = rec.dst_port

            # tcp_flags = rec.tcp_flags
            # ip_proto = rec.ip_proto
            # tos = rec.tos
            # src_as = rec.src_as
            # dst_as = rec.dst_as
            # src_mask = rec.src_mask
            # dst_mask = rec.dst_mask

            # XXX: Skip if nextHop is 0.0.0.0
            if nexthop == "0.0.0.0":
                klog.w("Skip when nextHop is 0.0.0.0: (%s)" % str(rec))
                return None, "nextHop is 0.0.0.0"

            # XXX: Inf is the port send netflow package
            # routerip is not must the loopback address
            inf = spi.scget("", "ipaddr", routerip)
            if not inf:
                klog.e("ERR: Not found:", routerip)
                return None, "Loopback not exists"

            loopback = inf["__loopback__"]

            dic = DotDict()

            dic.loopback.cur = loopback

            #
            # Flow Info
            #
            dic.addr.src = src_addr
            dic.addr.dst = dst_addr

            dic.port.nexthop = nexthop
            tmp = spi.scget("", "ipaddr", nexthop)
            if tmp:
                dic.loopback.nxt = tmp["__loopback__"]
            else:
                dic.loopback.nxt = "<%s: NotFound>" % (nexthop)
                klog.e("NotFound: nexthop: ", nexthop)
                return None, "nexthop not exists"

            dic["bytes"] = octets

            tmp = spi.scget(loopback, "ifindex", out_if)
            if tmp:
                dic.port.output = tmp["__ipaddr__"]
            else:
                dic.port.output = "<%s@%s>" % (out_if, loopback)
                klog.e("NotFound: %s@%s" % (out_if, loopback))

            tmp = spi.scget(loopback, "ifindex", in_if)
            if tmp:
                dic.port.input = tmp["__ipaddr__"]
            else:
                dic.port.input = "<%s@%s>" % (in_if, loopback)
                klog.e("NotFound: %s@%s" % (in_if, loopback))

            dic["_id"] = "{loopback.cur}::{addr.src}_to_{addr.dst}".format(**dic)

            diff = last - first
            bps = 8.0 * int(dic["bytes"]) * conf.SAMPLE_RATE / diff * 1000
            dic["bps"] = int(bps)

            dic.time.last = last
            dic.time.first = first

            dic.time.log = time.time()

            return dic, None
        except:
            klog.e(traceback.format_exc())
            klog.e("Except rec:", varfmt(rec, color=True))
            return None, "Except: %s" % traceback.format_exc()

    @staticmethod
    def savedic(dic):
        klog.d("Saving: ", varfmt(dic, color=True))
        db.logs.replace_one({"_id": dic["_id"]}, dic.todic(), True)

nfrp = NFRecProcessor




### ###########################################################
## NFProcessor - Act as a NF Server
#
class NFProcessor(miethread.MieThread):
    def __init__(self, conf, port=2055):
        self.conf = conf
        self.nfmon = nfmon.NFServer(port, self.onflow)

        miethread.MieThread.__init__(self)
        self.start()

    def act(self):
        self.nfmon.run()
        return 0

    def onflow(self, routerip, rec):
        dic, msg = nfrp.rec2dic(routerip, rec)
        nfp_recs.inc()
        if dic:
            nfp_recs_ok.inc()
            nfrp.savedic(dic)
        else:
            nfp_recs_ng.inc()
            klog.e("Error from rec2dic: ", msg)


### ###########################################################
## Request and Response
#
from bottle import get, post, put, delete, run, request

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
    odic.trans_id = indic.trans_id or 0xdeadbeef
    odic.ts = time.strftime("%Y%m%d%H%M%S")

    odic.result = DotDict()

    odic.err_code = 0
    odic.msg = None

    return odic


def getequip(uid):
    try:
        return DotDict(db.equips.find_one({"uid": uid}))
    except:
        traceback.print_exc()
        return {}


def getvlink(uid):
    try:
        return DotDict(db.vlinks.find_one({"uid": uid}))
    except:
        traceback.print_exc()
        return {}


def getport(uid):
    try:
        return DotDict(db.ports.find_one({"uid": uid}))
    except:
        traceback.print_exc()
        return {}


@post("/flow")
def docmd_flow():
    calldic = idic()

    klog.d(varfmt(calldic, "calldic"))

    request = calldic["request"]

    if request == "ms_flow_set_topo":
        return ms_flow_set_topo(calldic)

    if request == "ms_flow_get_flow":
        return ms_flow_get_flow(calldic)

    return "Bad request '%s'" % request



def ms_flow_set_topo(calldic=None):
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
                            // "capacity": 1000,
                            // "if_index": 1,
                            // "if_name": "ALU   1/1/4",
                            "ip_str": "10.0.140.11",
                            // "mac": "00-00-0A-00-8C-0B",
                            "type": 0,
                            "uid": "2"          // Global
                        },
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
            "vlinks": [
                {
                    // "bandwidth": 1000.0,
                    "dport": "26",          // port.uid
                    "sport": "3",
                    "uid": "12"             // Global
                },
                {
                    "bandwidth": 1000.0,
                    "dport": "38",
                    "sport": "13",
                    "uid": "13"
                },
                {
                    "bandwidth": 1000.0,
                    "dport": "43",
                    "sport": "44",
                    "uid": "50"
                }
            ]
        },
        "request": "ms_flow_set_topo",
        "trans_id": 1471572843,
        "ts": "20160819101403"
    }
    '''
    calldic = calldic or idic()

    #
    # Shortcuts
    #
    map_ip_router = {}                  # router ip_str
    map_portuid_port = {}               # port_uid => port


    #
    # Empty DB
    #
    db.equips.drop()
    db.vlinks.drop()
    db.ports.drop()

    equips = calldic["args"]["equips"]
    vlinks = calldic["args"]["vlinks"]

    for r in equips:
        map_ip_router[r["ip_str"]] = r

        ports = r["ports"]
        del r["ports"]

        r["_id"] = r["ip_str"]
        db.equips.replace_one({"_id": r["_id"]}, dict(r), True)

        for p in ports:
            map_portuid_port[p["uid"]] = p

            p["_id"] = p["ip_str"]
            p["router"] = r["ip_str"]
            db.ports.replace_one({"_id": p["_id"]}, dict(p), True)

            # TODO: Add ifindex and ip_str to each port if miss that

    for l in vlinks:
        try:
            l["_id"] = l["uid"]

            # XXX: >>> Additional information
            p = map_portuid_port.get(l.get("sport"))
            l["sportip"] = p.get("ip_str", "(Empty)")
            r = map_ip_router.get(p.get("router"))
            l["sloopbackip"] = r.get("ip_str")

            p = map_portuid_port.get(l.get("dport"))
            l["dportip"] = p.get("ip_str", "(Empty)")
            r = map_ip_router.get(p.get("router"))
            l["dloopbackip"] = r.get("ip_str")

            # XXX: <<< Additional information
            db.vlinks.replace_one({"_id": l["_id"]}, dict(l), True)

        except:
            traceback.print_exc()
            pass

    respdic = odic(calldic)
    res = json.dumps(respdic)

    spi.update()
    return res


def btok(n):
    return float(n) / 1024


def btom(n):
    return float(n) / 1024 / 1024


def btog(n):
    return float(n) / 1024 / 1024 / 1024


def equip_fr_port_ip(portip):
    # port_uid -> port
    tmp = spi.scget("", "ipaddr", portip)
    if tmp:
        equip = db.equips.find_one({"ip_str": tmp.get("__loopback__")})
        return equip
    return {}

def get_equip_flow(uid, limit=None, dir="o"):
    flows = []

    show = {
        "_id": 0,
        "bps": 1,
        "bytes": 1,
        "time.log": 1,
        "time.last": 1,
        "time.first": 1,
        "addr.src": 1,
        "addr.dst": 1,
        "port.nexthop": 1,
        "port.output": 1}

    equip = getequip(uid)
    if not equip:
        klog.e("No such equip, %s" % str(uid))
        return {}

    limit = limit or "40"
    dir = dir or "io"

    ip = equip["ip_str"]

    orlis = []
    if 'i' in dir:
        orlis.append({"loopback.nxt": ip})
    if 'o' in dir:
        orlis.append({"loopback.cur": ip})

    match = {"$or": orlis}

    logs = db.logs.find(match).sort("bps", pymongo.DESCENDING).limit(int(limit))
    tmq = time.time()
    for log in logs:
        try:
            timediff = time.time() - log["time"]["log"]
            if timediff > conf.DB_LOG_AGE_SKIP:
                continue

            bps = log["bps"]
            src = log["addr"]["src"]
            dst = log["addr"]["dst"]

            sportip = log["port"]["output"]
            dportip = log["port"]["nexthop"]

            src_equip = equip_fr_port_ip(sportip) or equip_fr_port_ip(log["loopback"]["cur"])
            dst_equip = equip_fr_port_ip(dportip) or equip_fr_port_ip(log["loopback"]["nxt"])

            seid = src_equip.get("uid", "<Null:output:%s>" % sportip)
            seip = src_equip.get("ip_str", "<Null:output:%s>" % sportip)
            spip = sportip
            deid = dst_equip.get("uid", "<Null:nexthop:%s>" % dportip)
            deip = dst_equip.get("ip_str", "<Null:nexthop:%s>" % dportip)
            dpip = dportip

            if ip == log["loopback"]["cur"]:
                direct = "LOOP" if deid == uid else "OUT"
            else:
                direct = "IN"

            # XXX: vlink = db.vlinks.find_one({"sportip": sportip, "dportip":
            # dportip})
            sloopbackip = src_equip.get("ip_str", "<Null>")
            dloopbackip = dst_equip.get("ip_str", "<Null>")

            vlink = db.vlinks.find_one(
                {"sloopbackip": sloopbackip, "dloopbackip": dloopbackip})
            vlink_uid = vlink["uid"] if vlink else "<Bad>"

            dirdic = {
                "dir": direct,
                "from": {
                    "equip_uid": seid,
                    "equip_ip": seip,
                    "port_ip": spip
                },
                "to": {
                    "equip_uid": deid,
                    "equip_ip": deip,
                    "port_ip": dpip
                }
            }

            last = log["time"]["last"]
            first = log["time"]["first"]

            _bps = "{:.3f}G or {:.3f}M or {:.3f}K".format(
                btog(bps), btom(bps), btok(bps))

            _flow = "(%s) >>> (%s)@(%s) >>> (%s)@(%s) >>> (%s)" % (src, spip, seip, dpip, deip, dst)
            flow = {
                "_flow": _flow,
                "_bps": _bps,
                "_dir": dirdic,
                "_bytes": log["bytes"],
                "bps": bps,
                "src": src,
                "dst": dst,
                "next_hop_uid": deid,
                "uid": vlink_uid,
                "_time": "%d - %d = %d" % (last, first, last - first)
            }
            flows.append(flow)
        except:
            klog.e(traceback.format_exc())
            klog.e("BAD LOG: ", varfmt(log, color=True))

    tmh = time.time()
    print "cost ...:", (tmh - tmq)
    return flows


def get_vlink_flow(uid):
    flows = []

    show = {
        "_id": 0,
        "bps": 1,
        "time.log": 1,
        "addr.src": 1,
        "addr.dst": 1
        }

    # vlink.sport, vlink.dport => db.ports.ui
    vlink = getvlink(uid)
    if not vlink:
        klog.e("NotFound: vlink: uid:", uid)
        return []

    klog.d(varfmt(vlink, "vlink"))

    sportip = vlink.get("sportip")
    dportip = vlink.get("dportip")

    src_equip = equip_fr_port_ip(sportip) or equip_fr_port_ip(vlink["sloopbackip"])
    dst_equip = equip_fr_port_ip(dportip) or equip_fr_port_ip(vlink["dloopbackip"])

    if not src_equip:
        klog.e("NotFound: src_equip: sportip:", sportip)
        return []

    next_hop_uid = dst_equip.get("uid", "<Null>")

    match = {"loopback.cur": src_equip["ip_str"], "port.nexthop": dportip}
    klog.d(varfmt(match, "db.logs.find: match"))
    logs = db.logs.find(match, show)
    for log in logs:
        try:
            timediff = time.time() - log["time"]["log"]
            if timediff > conf.DB_LOG_AGE_SKIP:
                continue

            _flow = "(%s) >>> (%s)@(%s) >>> (%s)@(%s) >>> (%s)" % (log["addr"]["src"], sportip, src_equip["ip_str"], dportip, dst_equip["ip_str"], log["addr"]["dst"])
            flow = {
                "_flow": _flow,

                "bps": log["bps"],
                "src": log["addr"]["src"],
                "dst": log["addr"]["dst"],
                "uid": uid,
                "next_hop_uid": next_hop_uid}
            flows.append(flow)
        except:
            klog.e(traceback.format_exc())
            klog.e("BAD LOG: ", varfmt(log, color=True))
            varprt(match, "find vlink")

    return flows



def ms_flow_get_flow(calldic=None):
    '''
    The request:
    {
        "args": {
            "router_uid": int(xxx) |
            "vlink_uid": int(xxx) |
        },
        "request": "ms_flow_get_flow",
        "trans_id": 1464768264,
        "ts": "20160601160424"
    }

    response:
    {
        "result": {
            "flows": [
                {
                    "bps": 23400,
                    "dst": "1.2.3.0",                   // srcAddr
                    "src": "219.141.189.200",           // dstAddr
                    "uid": "xxx"                        // vlink_uid
                },
                {
                    "bps": 43287,
                    "dst": "1.2.3.1",
                    "src": "219.141.189.201",
                    "uid": "f_1"
                },
                {
                    "bps": 63174,
                    "dst": "1.2.3.2",
                    "src": "219.141.189.202",
                    "uid": "f_2"
                }
            ]
        },
        "err_code": 0,
        "msg": "Demo response",
        "response": "ms_flow_get_flow",
        "trans_id": 1464768264,
        "ts": "20160601160424"
    }
    '''

    calldic = calldic or idic()

    varprt(calldic)
    respdic = odic(calldic)
    respdic.result = DotDict()

    vlink_uid = calldic.args.vlink_uid
    equip_uid = calldic.args.equip_uid

    if vlink_uid:
        respdic.result.flows = get_vlink_flow(vlink_uid)
    elif equip_uid:
        respdic.result.flows = get_equip_flow(equip_uid)

    return json.dumps(respdic)


spi.update()


### #####################################################################
# mcon etc
#
from roar.roar import CallManager, CmdServer_Socket
from roar import roarcmds

callman = CallManager(name="NetFlow")
cmdserv = CmdServer_Socket(callman, conf.CMDPORT)
cmdserv.start()

roarcmds.ExtCommands(callman, conf)

@callman.deccmd()
def objs(cmdctx, calldic):
    '''objs pat'''

    pat = calldic.nth_arg(0, ".*")
    pat = re.compile(pat)

    dic = {}
    for k, v in spi.portInfos.items():
        if pat.search(str(k)) or pat.search(str(v)):
            dic[k] = v
    return dic


@callman.deccmd()
def flowv(cmdctx, calldic):
    '''Show flow for vlink

    .opt --l limit :100

    .opt --hi bpsMin :9999999999999

    .opt --lo bpsMax :0

    .opt --s searchPat :.*

    .arg uids
    uid list
    '''

    limit = int(calldic.nth_opt("l", 0, 100))
    bpshi = int(calldic.nth_opt("hi", 0, 9999999999999))
    bpslo = int(calldic.nth_opt("lo", 0, 0))

    uids = calldic.get_args()
    if not uids:
        uids = [e.get("uid") for e in db.vlinks.find()]

    pat = calldic.nth_opt("s", 0, ".*")
    pat = re.compile(pat)

    klog.d(varfmt(uids, "UID List"))
    res = []
    for uid in uids:
        res.extend(get_vlink_flow(uid))
    res = [f for f in res if pat.search(str(f))]
    res = sorted(res, lambda x, y: y.get("bps", 0) - x.get("bps", 0))
    res = filter(lambda x: bpslo <= x.get("bps", 0) <= bpshi, res)
    return res[:limit]


@callman.deccmd()
def flowe(cmdctx, calldic):
    '''Show flow for vlink

    .opt --l limit :100

    .opt --hi bpsMin :9999999999999

    .opt --lo bpsMax :0

    .opt --s searchPat :.*

    .arg uids
    uid list
    '''


    uids = calldic.get_args()
    limit = calldic.nth_opt("l", 0, "100")
    dir = calldic.nth_opt("d", 0, "io")
    pat = calldic.nth_opt("s", 0, ".*")
    bpshi = int(calldic.nth_opt("hi", 0, 9999999999999))
    bpslo = int(calldic.nth_opt("lo", 0, 0))

    pat = re.compile(pat)

    if not uids:
        uids = [e.get("uid") for e in db.equips.find()]

    klog.d(varfmt(uids, "UID List"))
    res = []
    for uid in uids:
        res.extend(get_equip_flow(uid, None, dir))

    res = [f for f in res if pat.search(str(f))]
    res = sorted(res, lambda x, y: y.get("bps", 0) - x.get("bps", 0))
    res = filter(lambda x: bpslo <= x.get("bps", 0) <= bpshi, res)
    return res[:int(limit)]


@callman.deccmd()
def shortcuts(cmdctx, calldic):
    return spi.shortcuts


if __name__ == "__main__":
    '''
    lfp = LogFileProcessor(conf)
    conf.setmonitor(lambda x: lfp.wakeup())

    @callman.deccmd()
    def wakeup(cmdctx, calldic):
        lfp.wakeup()
        return "OK"
    '''

    nfp = NFProcessor(conf)

    run(server='paste', host='0.0.0.0', port=conf.BOTTLE_PORT, debug=conf.BOTTLE_DEBUG)
