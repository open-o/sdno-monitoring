#!/usr/bin/env python
# -*- coding: utf_8 -*-

# All the object from database

import os
import sys

sys.path.append("../common")

os.environ["KLOG_DFCFG"] = os.environ.get("KLOG_DFCFG", "/tmp/snmp.dfcfg")
os.environ["KLOG_RTCFG"] = os.environ.get("KLOG_RTCFG", "/tmp/snmp.rtcfg")
os.environ["KLOG_MASK"] = os.environ.get("KLOG_MASK", "facewindFHNS")

from utils import *
from xlogger import *

from bottle import get, post, put, delete, run, request

import miethread

import json
import time

### ###########################################################
## Singleton and klog
#
singleton("/tmp/snmp.pid", "Singleton check failed: snmp already exists")
setdebugable()

klog.to_stdout()
klog.to_file("/tmp/snmp%Y%R_%I.log")

### ###########################################################
# Read default configuration
#

### ###########################################################
# Everything is a NetObject
#
import netobject
import snmpsessionpool as ssp
import helper

portMan = netobject.PortMan()
siteMan = netobject.SiteMan()
venderMan = netobject.VenderMan()
routerMan = netobject.RouterMan()
linkMan = netobject.LinkMan()


helper.InfoDevMan.load(netobject.NetObjectMan)


def infoDev_load(cookie, objtype, hashkey, kwargs):
    if objtype != netobject.NetObject.ROUTER:
        print hashkey
        return

netobject.NetObjectMan.hookset(True, infoDev_load)

# Load redis to memory
netobject.NetObjectMan.load()


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

# getObjectById
# getObjectsByName
# getObjectsByPath

dic_ifname_ifinfo = {}


class Collector(miethread.MieThread):
    '''Thread pool to get data from snmp or netconf'''
    __metaclass__ = Singleton

    def __init__(self, name="SnmpCollector"):
        miethread.MieThread.__init__(self, name=name)
        self.start()

    def snmpdo(self, cookie):

        def doGetAll(r, cookie):
            print ">>>>> doGetAll:", r.ip_str, "comm:", r.community
            klog.d("TODO: filter out the unused ports")
            now = time.time()
            dic = helper.ifgetall(r.ip_str, r.community, 2)
            print "ifgetall, return:", len(dic)
            for k, v in dic.items():
                hashkey = "%s::%s" % (r.ip_str, v.ifDescr)

                tmp = dic_ifname_ifinfo.get(hashkey) or DotDict()

                tmp.oldval = tmp.newval
                tmp.newval = [now, v]

                print "doGetAll, set:", hashkey
                dic_ifname_ifinfo[hashkey] = tmp
            print "<<<<< doGetAll:", r.ip_str, "comm:", r.community
            print

        klog.d(">>> snmpdo, routerMan.foreach ...")
        routerMan.foreach(doGetAll, None)
        klog.d("<<< snmpdo, routerMan.foreach ...")

    def act(self):
        '''Fetch and save to db'''
        # DeferDo(self.snmpdo)
        self.snmpdo(None)
        return 10

snmpCollector = Collector()

@post("/link/links")
def docmd_ms_link_links():
    calldic = idic()

    klog.d(varfmt(calldic, "calldic"))

    request = calldic["request"]

    if request == "ms_link_set_links":
        return ms_link_set_links()

    if request == "ms_link_get_status":
        return ms_link_get_status()

    return "Bad request '%s'" % request


@post("/link/link")
def docmd_ms_link_set_links():
    calldic = idic()
    return ms_link_set_links(calldic)

def ms_link_set_links():
    '''
    The request:
    {
        "args": {
            "vlinks": [
                {
                    "equip": {
                        "community": "roastedchiken0",
                        "ip_str": "124.127.117.170",
                        "model": "aladin",
                        "name": "core0",
                        "ports": [
                            {
                                "if_index": "0",
                                "ip_str": "010.9.63.10",
                                "mac": "00:01:0E:03:25:20",
                                "type": 0,
                                "uid": "1000_0"
                            },
                        ],
                        "pos": "Old village of Gao",
                        "uid": "1000",
                        "vendor": "CISCO",
                        "x": 110.1,
                        "y": 46.4
                    },
                    "ports": [
                        {
                            "if_index": "0",
                            "ip_str": "010.9.63.10",
                            "mac": "00:01:0E:03:25:20",
                            "type": 0,
                            "uid": "1000_0"
                        }
                    ],
                    "uid": "v_0"
                },
            ]
        },
        "request": "ms_link_set_links",
        "trans_id": 1464244692,
        "ts": "20160526143812"
    }

    response:
    {
        "err_code": 0,
        "msg": "Demo response",
        "response": "ms_link_set_links",
        "result": {},
        "trans_id": 1464244692,
        "ts": "20160526143812"
    }
    '''

    calldic = idic()

    oldports, newports = set(), set()
    oldrouters, newrouters = set(), set()

    def get_oldrouters(o, oldrouters):
        oldrouters.add(o.__hashkey__)
    routerMan.foreach(get_oldrouters, oldrouters)

    def get_oldports(o, oldports):
        oldports.add(o.__hashkey__)
    portMan.foreach(get_oldports, oldports)

    vlinks = calldic["args"]["vlinks"]
    for vlink in vlinks:
        equip = vlink.get("equip")

        dic = DotDict()
        dic.uid = equip.get("uid")
        dic.name = equip.get("name")
        dic.vendor = equip.get("vendor")
        dic.community = equip.get("community")
        dic.ip_str = equip.get("ip_str")
        dic.pos = equip.get("pos")
        dic.x = equip.get("x")
        dic.y = equip.get("y")

        allowed = set(["uid", "name", "vender", "community",
                       "ip_str", "x", "y", "pos"])
        dic = {k: v for k, v in equip.items() if k in allowed}

        r = routerMan.get(False, **dic) or routerMan.get(True, **dic)
        newrouters.add(r.__hashkey__)

        # ports
        ports = vlink.get("ports")
        for port in ports:
            p = portMan.get(True, __router__=r.__hashkey__, **port)
            newports.add(p.__hashkey__)
            print "New port:", p.__hashkey__

    print "@@@oldrouters:", oldrouters
    print "@@@newrouters:", newrouters
    for hashkey in oldrouters.difference(newrouters):
        klog.d("TODO: Delete router: %s" % hashkey)
        try:
            netobject.NetObjectMan.rem(hashkey)
        except:
            pass

    print "@@@oldports:", oldports
    print "@@@newports:", newports
    for hashkey in oldports.difference(newports):
        klog.d("TODO: Delete Port: %s" % hashkey)
        try:
            netobject.NetObjectMan.rem(hashkey)
        except:
            pass

    respdic = odic(calldic)
    res = json.dumps(respdic)

    return res


@post("/link/status")
def docmd_ms_link_get_status():
    calldic = idic()
    return ms_link_get_status(calldic)


def ms_link_get_status():
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
            ]
        },
        "trans_id": 1464244693,
        "ts": "20160526143813"
    }

    '''

    calldic = idic()
    varprt(calldic)
    respdic = odic(calldic)

    respdic.result.utilization = []

    def dmp(o, utilization):
        obj = Obj()
        obj.port_uid = o.uid
        obj.if_name = o.if_name

        r = routerMan.find(o.__router__)
        if not r:
            print "Orphan port:", o.__hashkey__
            print "Router:", o.__router__
            return

        hashkey = "%s::%s" % (r.ip_str, o.if_name)

        vvv = dic_ifname_ifinfo.get(hashkey)
        if not vvv:
            print "Not found, hashkey: %s" % hashkey
            return

        if not vvv.oldval:
            print "Not ready (no vvv.oldval yet), hashkey: %s" % hashkey
            return

        print "vvv:", id(vvv), ", for hashkey:", hashkey
        try:
            oldval = vvv.oldval
            newval = vvv.newval

            varprt(oldval, "################ oldval ################:")
            varprt(newval, "################ newval ################:")

            deltaOut = int(newval[1].ifOutOctets) - int(oldval[1].ifOutOctets)
            ifSpeed = int(newval[1].ifSpeed)
            deltaSec = int(newval[0]) - int(oldval[0])

            # fix negative issue
            deltaOut += 0xffffffff
            deltaOut %= 0xffffffff

            obj.utilization = deltaOut * 8.0 * 100 / deltaSec / ifSpeed
            utilization.append(obj)
        except:
            print "XXX: ERR"
            pass

    portMan.foreach(dmp, respdic.result.utilization)
    # varprt(dic_ifname_ifinfo, "###################################:")

    return json.dumps(respdic)


@get("/objs/<cls>")
def docmd_objs(cls):
    calldic = idic()
    respdic = odic(calldic)
    respdic.result = []

    for o in netobject.NetObjectMan.objs_all().values():
        if cls == "all" or o.__objtype__ == cls:
            respdic.result.append(o)

    return json.dumps(respdic)


@get("/ifobjs")
def docmd_ifobjs():
    calldic = idic()
    respdic = odic(calldic)
    respdic.result = []

    for hashkey, inf in dic_ifname_ifinfo.items():
        print inf

    return json.dumps(dic_ifname_ifinfo)

run(server='paste', host='0.0.0.0', port=10000, debug=True)

