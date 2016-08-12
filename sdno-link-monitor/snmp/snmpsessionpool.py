#!/usr/bin/env python
# -*- coding: utf_8 -*-

import traceback
import time
from easysnmp import Session

from utils import *
import snmpsessionpool as ssp
import miethread

import netsnmp


class SnmpSession_netsnmp():

    def __init__(self, host, comm, vern, ttl):
        self.host = host
        self.comm = comm
        self.vern = vern
        self.sess = netsnmp.Session(DestHost=host, Community=comm, Version=vern)
        # self.sess.use_numeric = True
        # self.sess.use_sprint_value = True

        self.ttl = ttl
        self.access_time = time.time()

    def trans_value(self, val, type):
        '''Convert snmp type to python type'''

        return str(val)

        def miss(obj):
            print ">>> MISS:", type
            return str(obj)

        _maps = {
            "OCTETSTR": str,
            "TICKS": int,
            "INTEGER": int,
            "UNSIGNED32": int,
            "ENUM": int,
            "COUNTER": int,
            "GAUGE": int,
            "OBJECTID": str,
        }
        maps = {}
        return maps.get(type, miss)(val)

    def get(self, oid):
        '''Return err, val'''
        try:
            self.access_time = time.time()
            varlist = netsnmp.VarList(netsnmp.Varbind(oid))
            v = self.sess.get(varlist)
            return 0, self.trans_value(varlist[0].val, varlist[0].type)
        except:
            print "GET:", "-" * 30
            print "OID:", oid

            print "HOST:", self.host
            print "COMM:", self.comm
            print "VERN:", self.vern

            print "GET:", "-" * 30

            traceback.print_exc()
            return 1, None

    def walk(self, oid):
        try:
            self.access_time = time.time()
            varlist = netsnmp.VarList(netsnmp.Varbind(oid))
            items = self.sess.walk(varlist)
            return {
                i.iid: self.trans_value(
                    i.val,
                    i.type) for i in varlist}
        except:
            print "WALK:", "-" * 30
            print "OID:", oid

            print "HOST:", self.host
            print "COMM:", self.comm
            print "VERN:", self.vern

            print "WALK:", "-" * 30
            traceback.print_exc()
            print
            return {}




class SnmpSession_easysnmp():

    def __init__(self, host, comm, vern, ttl):
        self.host = host
        self.comm = comm
        self.vern = vern
        self.sess = Session(hostname=host, community=comm, version=vern)
        self.sess.use_numeric = True
        self.sess.use_sprint_value = True

        self.ttl = ttl
        self.access_time = time.time()

    def trans_value(self, value, type):
        '''Convert snmp type to python type'''

        return str(value)

        def miss(obj):
            print ">>> MISS:", type
            return str(obj)

        _maps = {
            "OCTETSTR": str,
            "TICKS": int,
            "INTEGER": int,
            "UNSIGNED32": int,
            "ENUM": int,
            "COUNTER": int,
            "GAUGE": int,
            "OBJECTID": str,
        }
        maps = {}
        return maps.get(type, miss)(value)

    def get(self, oid):
        '''Return err, val'''
        try:
            self.access_time = time.time()
            v = self.sess.get(oid)
            return 0, self.trans_value(v.value, v.snmp_type)
        except:
            print "GET:", "-" * 30
            print "OID:", oid

            print "HOST:", self.host
            print "COMM:", self.comm
            print "VERN:", self.vern

            print "GET:", "-" * 30

            traceback.print_exc()
            return 1, None

    def walk(self, oid):
        try:
            self.access_time = time.time()
            items = self.sess.walk(oid)
            return {
                i.oid_index: self.trans_value(
                    i.value,
                    i.snmp_type) for i in items}
        except:
            print "WALK:", "-" * 30
            print "OID:", oid

            print "HOST:", self.host
            print "COMM:", self.comm
            print "VERN:", self.vern

            print "WALK:", "-" * 30
            traceback.print_exc()
            print
            return {}

SnmpSession = SnmpSession_netsnmp
SnmpSession = SnmpSession_easysnmp

class SnmpSessionPool():
    # key: "{host}:{comm}:{vern}", val: SnmpSession
    _sessions = {}

    @classmethod
    def get(cls, host="localhost", comm="public", vern=2, new=True, ttl=600):
        hashkey = "%s:%s:%s" % (host, comm, vern)

        s = cls._sessions.get(hashkey)
        if not s and new:
            s = SnmpSession(host, comm, vern, ttl)
            print "Creating SnmpSession:", hashkey
            cls._sessions[hashkey] = s
        print
        return s

    @classmethod
    def rem(cls, hashkey):
        try:
            del cls._sessions[hashkey]
            print "SnmpSessionPool.rem:", hashkey
        except:
            pass

    @classmethod
    def foreach(cls, func, cookie):
        for hashkey, session in cls._sessions.items():
            func(hashkey, session, cookie)

ssp = SnmpSessionPool()


class SnmpSessionCleaner(miethread.MieThread):
    __metaclass__ = Singleton

    def __init__(self, name="zbd"):
        miethread.MieThread.__init__(self, name=name)
        self.start()

    def act(self):
        '''Fetch and save to db'''
        exps = []

        def checkttl(hashkey, session, exps):
            # print "checkttl:", hashkey
            now = time.time()
            if now > session.ttl + session.access_time:
                exps.append(hashkey)

        SnmpSessionPool.foreach(checkttl, exps)

        for hashkey in exps:
            # print "Remove from SSP:", hashkey
            SnmpSessionPool.rem(hashkey)

        return 10

ssc = SnmpSessionCleaner()
