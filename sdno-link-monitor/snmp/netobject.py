#!/usr/bin/env python
# -*- coding: utf_8 -*-

import traceback
from utils import *

### ###########################################################
# Everything is a NetObject
#


class NetObject(DotDict):
    SITE = "site"
    PORT = "port"
    VENDER = "vender"
    ROUTER = "router"
    LINK = "link"
    VLINK = "vlink"

    def __init__(self, objtype, hashkey, **kwargs):
        DotDict.__init__(self, **kwargs)

        self.__objtype__ = objtype
        self.__hashkey__ = hashkey
        self.__dirty__ = True

    def objtype(self):
        return self.__objtype__

    def hashkey(self):
        return self.__hashkey__


class NetObjectMan(object):
    __metaclass__ = Singleton

    # All the Objects (Elemental Information that saved in DB)
    _all_objects = {}

    # hooks called when net object changed.
    _ahooks = []
    _bhooks = []

    @classmethod
    def objs_all(cls):
        return cls._all_objects

    @classmethod
    def hookset(cls, ahook, hookfunc, cookie=None):
        hooks = cls._ahooks if ahook else cls._bhooks
        hooks.append([hookfunc, cookie])

    @classmethod
    def hookcall(cls, ahook, objtype, hashkey, kwargs):
        hooks = cls._ahooks if ahook else cls._bhooks
        for hookfunc, cookie in hooks:
            hookfunc(cookie, objtype, hashkey, kwargs)

    @classmethod
    def load(cls):
        '''Save to DB'''
        r = redis.Redis(db=13)
        for key in r.scan_iter():
            dic = r.hgetall(key)

            hashkey = dic.get("__hashkey__")
            if not hashkey:
                continue

            objtype = dic.get("__objtype__")
            if not objtype:
                continue

            o = NetObject(objtype, hashkey, **dic)
            NetObjectMan._all_objects[hashkey] = o
            NetObjectMan._all_objects[hashkey] = o

    @classmethod
    def save(cls):
        '''Save to DB'''
        r = redis.Redis(db=13)
        for o in NetObjectMan._all_objects.values():
            if o.__dirty__:
                o.__dirty__ = False
                r.hmset(o.hashkey(), o)

    def __init__(self, objtype):
        self.objtype = objtype

    def hashkey(self, **kwargs):
        raise KeyError

    def find(self, hashkey):
        return NetObjectMan._all_objects.get(hashkey)

    def get(self, new, **kwargs):
        hashkey = self.hashkey(**kwargs)

        o = NetObjectMan._all_objects.get(hashkey)
        if not o and new:
            NetObjectMan.hookcall(False, self.objtype, hashkey, kwargs)
            o = NetObject(self.objtype, hashkey, **kwargs)
            NetObjectMan._all_objects[hashkey] = o
            NetObjectMan.hookcall(True, self.objtype, hashkey, kwargs)
            o.__dirty__ = True

            NetObjectMan.save()
        return o

    @classmethod
    def rem(cls, hashkey):
        print ">>> REM >>>:", hashkey
        try:
            r = redis.Redis(db=13)
            r.delete(hashkey)
        except:
            pass

        try:
            del NetObjectMan._all_objects[hashkey]
        except:
            pass

    def foreach(self, func, cookie):
        for o in NetObjectMan._all_objects.values():
            if o.objtype() == self.objtype:
                func(o, cookie)


class PortMan(NetObjectMan):
    '''
    class Port:
        uid
        if_index
        ip_str
        mac
        type
        uid

    key:
        mac
    '''

    def __init__(self):
        NetObjectMan.__init__(self, NetObject.PORT)

    def hashkey(self, **kwargs):
        '''Generate a hash key'''
        if_name = kwargs.get("if_name").replace(":", "_").replace("/", "_").replace("-", "_")
        router = kwargs.get("__router__").split(":", 1)[1]
        return "PORT:%s:%s" % (router, if_name)


class SiteMan(NetObjectMan):
    '''One list for all the Site

    class Site:
        name
        x
        y

    key:
        name + x + y
    '''

    def __init__(self):
        NetObjectMan.__init__(self, NetObject.SITE)

    def hashkey(self, **kwargs):
        '''Generate a hash key'''
        return "SITE:{name}:{x}:{y}".format(**kwargs)


class VenderMan(NetObjectMan):
    '''One list for all the Site

    class Vender:
        name
    '''

    def __init__(self):
        NetObjectMan.__init__(self, NetObject.VENDER)

    def hashkey(self, **kwargs):
        '''Generate a hash key'''
        return "VENDER:{name}".format(**kwargs)


class RouterMan(NetObjectMan):
    '''One list for all the Site

    class Router:
        community
        ip_str
        model
        name
        vender
    '''

    def __init__(self):
        NetObjectMan.__init__(self, NetObject.ROUTER)

    def hashkey(self, **kwargs):
        '''Generate a hash key'''
        key = "ROUTER:{name}".format(**kwargs)
        return key


### ###########################################################
# Link/VLink?
#
class LinkMan(NetObjectMan):
    '''One list for all the Site

    class Router:
        community
        ip_str
        model
        name
        vender
    '''

    def __init__(self):
        NetObjectMan.__init__(self, NetObject.LINK)

    def hashkey(self, **kwargs):
        '''Generate a hash key'''
        return "LINK:{name}".format(**kwargs)
