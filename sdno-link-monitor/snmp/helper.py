#!/usr/bin/env python
# -*- coding: utf_8 -*-

from utils import *
import snmpsessionpool as ssp


class InfoDevMan(object):

    _infoDevs = {}

    @classmethod
    def load(cls, netobjman):

        for k, v in netobjman.objs_all().items():
            print "Will Create InfoDev"


# batchGet(["aaa", "bbb"], False)
def batchGet(names, errbrk=True):
    dic = {}
    for name in names:

        # Get infoDevs that support this nick name
        # TODO: infoDevs = Map_NickModu.get(name) or []

        infoDevs = infoDevMan.infoDevs
        for infoDev in infoDevs:
            # res: { errcode=Int, errdesc=Str, content=Obj }
            res = infoDev.get(name)
            if errbrk and res.get("errcode"):
                return dic
            dic[name] = res
    return dic


class InfoEnt():

    def __init__(self):
        self.updatetime = time.time()

        self.oldval = None
        self.oldtime = None

        self.newval = None
        self.newtime = None


class InfoEnt_Snmp():

    def get(self, oid):
        ss = ssp.ssp.get("localhost", ttl=20)
        print "AAAA:", ss
        res = ss.get("iso.3.6.1.2.1.1.1.0")


class InfoEnt_Func():

    def get(self, oid):
        pass


class InfoEnt_Memory():

    def get(self, oid):
        pass

'''
#
# This is the RULE
#
{
    "infoDev_Name": {
        type: "Router",

        Entries : {
            "ifNumber": {
                class: memory,  # How to access it?
            },
            "ifNumber": {
                class: snmp,    # define the collector, this is predefined
                time: 1000000   # how long time to collect
                snmp: {
                    oid: ".1.3.6.1.2.1.2.1.0",
                }
            },
            "if_0_speed": {
                exported: True,
            },

        }
    }
}

'''

dic_if_oid_name = {
    ## ".1.3.6.1.2.1.2.2.1.1": "ifIndex",
    ".1.3.6.1.2.1.2.2.1.2": "ifDescr",
    ## ".1.3.6.1.2.1.2.2.1.3": "ifType",
    # ".1.3.6.1.2.1.2.2.1.4": "ifMtu",
    ".1.3.6.1.2.1.2.2.1.5": "ifSpeed",
    ".1.3.6.1.2.1.2.2.1.6": "ifPhysAddress",
    ## ".1.3.6.1.2.1.2.2.1.7": "ifAdminStatus",
    # ".1.3.6.1.2.1.2.2.1.9": "ifLastChange",
    ## ".1.3.6.1.2.1.2.2.1.10": "ifInOctets",
    # ".1.3.6.1.2.1.2.2.1.11": "ifInUcastPkts",
    # ".1.3.6.1.2.1.2.2.1.12": "ifInNUcastPkts",
    # ".1.3.6.1.2.1.2.2.1.13": "ifInDiscards",
    # ".1.3.6.1.2.1.2.2.1.14": "ifInErrors",
    # ".1.3.6.1.2.1.2.2.1.15": "ifInUnknownProtos",
    ".1.3.6.1.2.1.2.2.1.16": "ifOutOctets",
    # ".1.3.6.1.2.1.2.2.1.17": "ifOutUcastPkts",
    # ".1.3.6.1.2.1.2.2.1.18": "ifOutNUcastPkts",
    # ".1.3.6.1.2.1.2.2.1.19": "ifOutDiscards",
    # ".1.3.6.1.2.1.2.2.1.20": "ifOutErrors",
    # ".1.3.6.1.2.1.2.2.1.21": "ifOutQLen",
}

dic_if_name_oid = {v: k for k, v in dic_if_oid_name.items()}


def ifgetall(host, comm, vern):
    ss = ssp.ssp.get(host, comm, vern)

    dic_index_ifdev = {}
    walks, gets = 0, 0

    for oid, name in dic_if_oid_name.items():
        res = ss.walk(oid)
        walks += 1
        for oid_index, val in res.items():
            # oid_index = 6143, oid = ".1.3.6.1.2.1.2.2.1.1" + oid_index
            inf = dic_index_ifdev.get(oid_index)
            gets += 1
            if not inf:
                inf = DotDict()
                dic_index_ifdev[oid_index] = inf
            inf[name] = val

    klog.d("Summary: Walks:%d, Gets:%d" % (walks, gets))
    return dic_index_ifdev


#
# For a given class of router
#
class InfoDev():

    def __init__(self, name="InfoDev"):
        self.name = name

        # nickname <> [tryThis, tryThat, tryOthers]
        # self.tryLis = {}

        # TODO: Load rule and fill this?
        self.infoEnts = {}

    def has(self, name):
        '''Check if this name supported by this module'''
        pass

    def get(self, name):
        '''Return Query result according to this name'''

        tryLis = self.tryLis.get(name)
        for t in tryLis:
            t.get(name)
        return {errcode: 0, errdesc: None, content: None}
