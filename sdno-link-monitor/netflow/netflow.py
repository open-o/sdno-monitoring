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


import os
import sys
import shutil
import datetime

sys.path.append("../common")

os.environ["KLOG_DFCFG"] = os.environ.get("KLOG_DFCFG", "/tmp/netflow.dfcfg")
os.environ["KLOG_RTCFG"] = os.environ.get("KLOG_RTCFG", "/tmp/netflow.rtcfg")
os.environ["KLOG_MASK"] = os.environ.get("KLOG_MASK", "facewindFHNS")

from utils import *
import confcenter
from xlogger import *
from singleton import *
from bprint import *
from deferdo import *

from bottle import get, post, put, delete, run, request

import miethread

import json
import time

### ###########################################################
## Singleton and klog
#
### Appsingleton("/tmp/netflow.pid", "Singleton check failed: netflow already exists")
# setdebugable()

klog.to_stdout()
klog.to_file("/tmp/netflow_%Y%R_%I.log")

import pymongo
client = pymongo.MongoClient()
db = client.netflow

db.logs.ensure_index([("_id", pymongo.ASCENDING),
                      ("loopback", pymongo.ASCENDING),
                      ("nLoopback", pymongo.ASCENDING),
                      ("oPortIp", pymongo.ASCENDING),
                      ("nPortIp", pymongo.ASCENDING)])
db.vlinks.ensure_index([("_id", pymongo.ASCENDING),
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


class Counter():

    def __init__(self, name=None):
        self.name = name or "ZBD"
        self.dic = {}

    def clr(self):
        self.dic = {}

    def add(self, ent, inc=1):
        self.dic[ent] = self.dic.get(ent, 0) + inc

    def dic(self):
        return self.dic

    def dmp(self):
        varprt(self.dic, self.name)


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
        ctime = datetime.datetime.now() - datetime.timedelta(seconds=self.keeptime)

        query = {"ctime": {"$lt": ctime}}
        res = db.logs.delete_many(query)
        klog.d("%s" % varfmt(query))
        klog.d("%d deleted." % res.deleted_count)

        return self.keeptime * 9 / 10

lc = LogCleaner(60 * 45)


class LogFileProcessor(miethread.MieThread):
    __metaclass__ = ClsSingleton

    def __init__(self, logdir, bakdir=None):
        self.logdir = logdir
        self.bakdir = bakdir

        miethread.MieThread.__init__(self)
        self.start()

        self.nglis_iPortIp = Counter("NGLIST::iPortIp")
        self.nglis_oPortIp = Counter("NGLIST::oPortIp")
        self.nglis_nLoopback = Counter("NGLIST::nLoopback")
        self.nglis_ipaddr = Counter("NGLIST::ipAddr")

    def act(self):
        files = self.get_files(self.logdir) or []

        varfmt(files)

        klog.d("%d files in queue" % len(files))
        tmq = time.time()
        self.parse(files)
        tmh = time.time()
        klog.d("%d files processed, in time %f" % (len(files), tmh - tmq))

        return 60

    def get_files(self, dir):
        '''Get all the log files.
        NOTE: the last one is skipped, cause it may been written now'''

        def fnameok(s):
            l = len(s)
            return l >= 27 and l <= 35 and s.endswith(".txt")

        try:
            for root, dirs, files in os.walk(dir):
                # lis = sorted(filter(lambda f: f.endswith(".txt"), files))[0:-1]
                lis = filter(fnameok, files)
                lis.sort(key=lambda x: x[-19:-4])
                res = [os.path.join(root, f) for f in lis[0:-1]]

                return res
        except:
            return []

    def gen_log(self, line):
        '''
        flowInfo:
            srcAddr
            srcPort
            dstAddr
            dstPort

            bytes
            ctime

        equip:
            loopback - The port address send this netflow package, This Router IP or loopback
            iportIp - Input Port IP
            oportIp - Output Port IP
            nportIp - Next Port Ip, NextHop

            nrouterip - Next Routers IP (snmp host IP)
        '''
        try:
            segs = line.strip().split(",")
            if not segs or len(segs) < 14:
                return None

            # XXX: Skip if nextHop is 0.0.0.0
            if segs[4] == "0.0.0.0":
                return None

            # XXX: Inf is the port send netflow package
            # segs[0] is not must the loopback address
            inf = spi.scget("", "ipaddr", segs[0])
            if not inf:
                # print "ERR: Not found:", segs[0]
                self.nglis_ipaddr.add(segs[0])
                return None

            loopback = inf["__loopback__"]

            '''
            if segs[2] == "10.0.148.15" and segs[3] == "10.0.248.25" and segs[4] == "10.0.111.1":
                print "xxxxxxxxxxxxxxxxxxxxx"
            '''

            #
            # dic.ctime - timestamp for this record
            # dic.rpt
            #
            dic = DotDict()

            dic["loopback"] = loopback
            dic["ctime"] = datetime.datetime.strptime(
                segs[1], "%Y-%m-%d %H:%M:%S")

            #
            # Flow Info
            #
            dic["srcAddr"] = segs[2]
            dic["dstAddr"] = segs[3]

            # segs[4] is nextHop
            dic["nPortIp"] = segs[4]
            tmp = spi.scget("", "ipaddr", segs[4])
            if tmp:
                dic["nLoopback"] = tmp["__loopback__"]
            else:
                # print "nLoopback: getFromIP NG: ", segs[4]
                self.nglis_nLoopback.add(segs[4])
                return None

            ### dic["dpkt"] = segs[5]
            dic["bytes"] = int(segs[6])

            ### dic["srcMask"] = segs[7]
            ### dic["dstMask"] = segs[8]

            ### dic["ifIndexOut"] = segs[9]
            tmp = spi.scget(loopback, "ifindex", segs[9])
            if tmp:
                dic["oPortIp"] = tmp["__ipaddr__"]
            else:
                # print "iPortIp: getFromIP NG: ", segs[9]
                self.nglis_oPortIp.add(segs[9])

            ### dic["ifIndexIn"] = segs[10]
            tmp = spi.scget(loopback, "ifindex", segs[10])
            if tmp:
                dic["iPortIp"] = tmp["__ipaddr__"]
            else:
                # print "oPortIp: getFromIP NG: ", segs[10]
                self.nglis_iPortIp.add(segs[10])

            ### dic["srcPort"] = segs[11]
            ### dic["dstPort"] = segs[12]

            ### dic["version"] = segs[13]

            dic["_id"] = "{loopback}::{srcAddr}_{dstAddr}".format(**dic)

            return dic
        except:
            traceback.print_exc()
            return None

    def parse(self, files):
        self.nglis_iPortIp.clr()
        self.nglis_oPortIp.clr()
        self.nglis_nLoopback.clr()
        self.nglis_ipaddr.clr()

        allcnt = 0
        allrev = 0
        alltmq = time.time()
        for name in files:
            tmq = time.time()
            cnt = 0
            rev = 0
            with open(name, "rt") as f:
                lnr = 0
                for l in f:
                    lnr += 1
                    dic = self.gen_log(l)
                    if not dic:
                        continue

                    dic["logfile"] = name
                    dic["lnr"] = lnr

                    cnt += 1
                    # 1. Got the old with same flow
                    # 2. Calc the bps
                    bps = 0
                    x = db.logs.find_one({"_id": dic["_id"]})
                    # x = db.logs.find({"_id": dic["_id"]}).sort([("ctime",pymongo.ASCENDING)]).limit(1)
                    if x:
                        oldtime = x["ctime"]
                        newtime = dic["ctime"]

                        diff = (newtime - oldtime).total_seconds() or 1.0
                        bps = 8.0 * int(dic["bytes"]) * 5000 / diff

                        dic["oldtime"] = x["ctime"]
                        dic["oldlogfile"] = x["logfile"]
                        dic["oldln"] = x["lnr"]
                        dic["deltaSeconds"] = diff

                        if bps < 0:
                            rev += 1
                            # XXX: only for test
                            break
                            print "..... oldLog :", x.get("logfile")
                            print "..... newLog :", dic.get("logfile")
                            print "...... oldLn :", x.get("lnr")
                            print "...... newLn :", dic.get("lnr")
                            print ".... oldtime :", oldtime
                            print ".... newtime :", newtime
                            print "....... diff :", diff
                            print "...... bytes :", dic["bytes"]
                            print
                    else:
                        print dic
                        klog.d("No log found: %s" % str({"_id": dic["_id"]}))

                    dic["bps"] = bps

                    if dic:
                        # print "{routerIp}: {srcAddr} ->
                        # {dstAddr}".format(**dic)
                        db.logs.replace_one({"_id": dic["_id"]}, dic, True)

            # XXX: Only for testing
            tmh = time.time()
            '''
            klog.d("<<< Processing: '%s', lines: %04d, cost:%f, eachCost:%f" %
                   (name, cnt, (tmh - tmq), (tmh - tmq) / (cnt + 1)))
            '''

            allcnt += cnt
            allrev += rev

            # Backup after processed
            if self.bakdir:
                try:
                    shutil.move(name, self.bakdir)
                except:
                    print "move ng:", name
                    try:
                        os.remove(name)
                    except:
                        print "remove ng:", name

        alltmh = time.time()

        self.nglis_iPortIp.dmp()
        self.nglis_oPortIp.dmp()
        self.nglis_nLoopback.dmp()
        self.nglis_ipaddr.dmp()

        print "allcnt:", allcnt
        print "allrev:", allrev
        print "alltme:", (alltmh - alltmq)

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
    odic.trans_id = indic.trans_id or 0xdeadbeef
    odic.ts = time.strftime("%Y%m%d%H%M%S")

    odic.result = DotDict()

    odic.err_code = 0
    odic.msg = None

    return odic


def getequip(uid):
    try:
        return db.equips.find_one({"uid": uid})
    except:
        traceback.print_exc()
        return {}


def getvlink(uid):
    try:
        return db.vlinks.find_one({"uid": uid})
    except:
        traceback.print_exc()
        return {}


def getport(uid):
    try:
        return db.ports.find_one({"uid": uid})
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


map_uid_router = {}
map_ip_router = {}

map_portuid_router = {}
map_portuid_port = {}
map_portip_router = {}
map_portip_port = {}


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

    db.equips.drop()
    db.vlinks.drop()
    db.ports.drop()

    equips = calldic["args"]["equips"]
    vlinks = calldic["args"]["vlinks"]

    for r in equips:
        map_uid_router[r["uid"]] = r
        map_ip_router[r["ip_str"]] = r

        ports = r["ports"]
        del r["ports"]

        r["_id"] = r["ip_str"]
        db.equips.replace_one({"_id": r["_id"]}, r, True)

        for p in ports:
            map_portuid_router[p["uid"]] = r
            map_portuid_port[p["uid"]] = p
            map_portip_router[p["ip_str"]] = r
            map_portip_port[p["ip_str"]] = p

            p["_id"] = p["ip_str"]
            p["router"] = r["ip_str"]
            db.ports.replace_one({"_id": p["_id"]}, p, True)

            # TODO: Add ifindex and ip_str to each port if miss that

    for l in vlinks:
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
        db.vlinks.replace_one({"_id": l["_id"]}, l, True)

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


def get_equip_flow(uid, limit=None, dir="o"):
    flows = []

    show = {
        "_id": 0,
        "bps": 1,
        "bytes": 1,
        "ctime": 1,
        "srcAddr": 1,
        "dstAddr": 1,
        "nPortIp": 1,
        "oPortIp": 1}

    def equip_fr_port_ip(portip):
        '''
        r = map_portip_router.get(portip)
        if r:
            return r.get("uid")
        return "<404>:%s" % portip
        '''

        # port_uid -> port
        tmp = spi.scget("", "ipaddr", portip)
        print "xxxxxxxxxxxxxxxxxxxxxxxx"
        print tmp
        print "xxxxxxxxxxxxxxxxxxxxxxxx"
        if tmp:
            equip = db.equips.find_one({"ip_str": tmp.get("__loopback__")})
            print "equip:", equip
            return equip
        return {}
        '''
        port = db.ports.find_one({"ip_str": portip})
        if port:
            equip = db.equips.find_one({"ip_str": port.get("router")})
            return equip
        return {}
        '''

    equip = getequip(uid)
    if not equip:
        return {}

    limit = limit or "40"
    dir = dir or "io"

    ip = equip["ip_str"]

    orlis = []
    if 'i' in dir:
        orlis.append({"nLoopback": ip})
    if 'o' in dir:
        orlis.append({"loopback": ip})

    match = {"$or": orlis}

    logs = db.logs.find(match).sort(
        "bps", pymongo.DESCENDING).limit(
        int(limit))
    tmq = time.time()
    for log in logs:
        bps = log.get("bps")
        src = log.get("srcAddr")
        dst = log.get("dstAddr")

        sportip = log.get("oPortIp")
        dportip = log.get("nPortIp")

        src_equip = equip_fr_port_ip(sportip)
        dst_equip = equip_fr_port_ip(dportip)

        seid = src_equip.get("uid", "<Null>")
        seip = src_equip.get("ip_str", "<Null>")
        spip = sportip
        deid = dst_equip.get("uid", "<Null>")
        deip = dst_equip.get("ip_str", "<Null>")
        dpip = dportip

        if ip == log.get("loopback"):
            direct = "LOOP" if deid == uid else "OUT"
        else:
            direct = "IN"

        # XXX: vlink = db.vlinks.find_one({"sportip": sportip, "dportip":
        # dportip})
        sloopbackip = src_equip.get("ip_str", "<Null>")
        dloopbackip = dst_equip.get("ip_str", "<Null>")

        vlink = db.vlinks.find_one(
            {"sloopbackip": sloopbackip, "dloopbackip": dloopbackip})
        if vlink:
            vlink_uid = vlink["uid"]
        else:
            vlink_uid = "BADVLINK"

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

        logtime = log.get("ctime")
        nowtime = datetime.datetime.now()
        timedic = {
            "logtime": str(logtime),
            "nowtime": str(nowtime),
            "timediff": (nowtime - logtime).total_seconds()
        }
        print "ddddddddddddddddddddddddddd"
        print "ddddddddddddddddddddddddddd"
        print "ddddddddddddddddddddddddddd"
        print "ddddddddddddddddddddddddddd"
        print type(log.get("ctime"))
        print "ddddddddddddddddddddddddddd"
        print "ddddddddddddddddddddddddddd"
        print "ddddddddddddddddddddddddddd"
        print "ddddddddddddddddddddddddddd"

        _bps = "{:.3f}G or {:.3f}M or {:.3f}K".format(
            btog(bps), btom(bps), btok(bps))
        flow = {
            "bps": bps,
            "_bps": _bps,
            "src": src,
            "dst": dst,
            "_dir": dirdic,
            "_bytes": log.get("bytes"),
            "_time": timedic,
            "next_hop_uid": deid,
            "uid": vlink_uid
        }
        flows.append(flow)

    tmh = time.time()
    print "cost ...:", (tmh - tmq)
    return flows


def get_vlink_flow(uid):
    flows = []

    show = {
        "_id": 0,
        "bps": 1,
        "srcAddr": 1,
        "dstAddr": 1,
        "nPortIp": 1,
        "oPortIp": 1}

    # vlink.sport, vlink.dport => db.ports.ui
    vlink = getvlink(uid)
    if vlink:
        sportip = vlink.get("sportip")
        dportip = vlink.get("dportip")

        next_hop_uid = equip_fr_port_ip(dportip)

        match = {"oPortIp": sportip, "nPortIp": dportip}
        varprt(match, "find vlink")
        items = db.logs.find(match, show)
        for i in items:
            flow = {
                "bps": i.get("bps"),
                "src": i.get("srcAddr"),
                "dst": i.get("dstAddr"),
                "uid": uid,
                "next_hop_uid": next_hop_uid}
            flows.append(flow)

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

    vlink_uid = calldic["args"].get("vlink_uid")
    equip_uid = calldic["args"].get("equip_uid")

    if vlink_uid:
        respdic.result.flows = get_vlink_flow(vlink_uid)
    elif equip_uid:
        respdic.result.flows = get_equip_flow(equip_uid)

    return json.dumps(respdic)


spi.update()
# varprt(spi.portInfos)


### #####################################################################
# mcon etc
#
from roar import CallManager, CmdServer_Socket
callman = CallManager()
cmdserv = CmdServer_Socket(callman, 9021)
cmdserv.start()


@callman.deccmd()
def objs(cmdctx, calldic):
    '''objs pat'''

    arg = calldic.get_args()
    pat = arg[0] if arg else None

    if not pat:
        return spi.portInfos.items()

    dic = {}
    for k, v in spi.portInfos.items():
        if str(k).find(pat) >= 0 or str(v).find(pat) >= 0:
            dic[k] = v
    return dic


@callman.deccmd()
def flowv(cmdctx, calldic):
    uid = calldic.get_args[0]
    return get_vlink_flow(uid)


@callman.deccmd()
def flowe(cmdctx, calldic):
    '''flowe --u uid --l limit --d dir pat'''

    opt = calldic.get_opt("u")
    uid = opt[-1] if opt else "1"

    opt = calldic.get_opt("l")
    limit = opt[-1] if opt else "100"

    opt = calldic.get_opt("d")
    dir = opt[-1] if opt else "io"

    arg = calldic.get_args()
    pat = arg[0] if arg else None

    res = get_equip_flow(uid, limit, dir)
    if not pat:
        return res
    return [f for f in res if (str(f).find(pat) >= 0)]


@callman.deccmd()
def shortcuts(cmdctx, calldic):
    return spi.shortcuts


@callman.deccmd()
def restart(cmdctx, calldic):
    '''Quit this script'''
    def seeya(cookie):
        time.sleep(1)
        os._exit(0)

    DeferDo(seeya)
    return "Bye"


if __name__ == "__main__":
    # lfp = LogFileProcessor("../../jnca", "../../jnca/bankup2")
    #lfp = LogFileProcessor("../../jnca")
    # lfp = LogFileProcessor("../../jnca", "../../jnca/bankup4")
    #lfp = LogFileProcessor("../../jnca/bankup3")
    # lfp = LogFileProcessor("../../jnca")
    lfp = LogFileProcessor("../../jnca", "../../jnca/bak0906")
    # lfp = LogFileProcessor("../../jnca/bak0906")

    run(server='paste', host='0.0.0.0', port=10001, debug=True)
