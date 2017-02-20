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

import re
from locktan import locktan

### ###########################################################
## Statistic Information
#

# Key = Name, Val = Number


class KStat(object):
    _inf = {}
    _dsc = {}
    _fun = {}

    @classmethod
    def dmp(cls, what=None, verb=False, asdict=True):
        ''' dump stat entries

        -v - verbose:
            lc.log.__dsc__ = xxxxxx
            aa.count.__dsc__ = 3

        -l - list:
            lc.log=2
            aa.count=3

        -d = dict:
            "lc.log": {
                "val": 234234,
                "dsc": "Log count for LC module",
            }
        '''

        d = {}

        if not what:
            what = ".*"

        try:
            what = ".*" + what[0] + ".*"
            pat = re.compile(what)
        except:
            pat = re.compile(".*")

        for k, v in cls._fun.items():
            d[k] = v[0](v[1])

        for k, v in cls._inf.items():
            d[k] = v

        # keys should be shown
        keys = [k for k in d if pat.search(k)]
        keys.sort(lambda a, b: cmp(a[2:], b[2:]))

        if asdict:
            dic = {}

            for key in keys:
                sub = {"val": d[key]}
                if verb and key in cls._dsc:
                    dsc["dsc"] = cls._dsc.get(key)
                dic[key] = sub

            return dic
        else:
            newlist = []
            oldgroup = ""
            for key in keys:
                try:
                    groups = key.split(".")
                    if groups:
                        group = groups[0]
                        if oldgroup != group:
                            newlist.append("")
                            oldgroup = group
                except:
                    pass

                newlist.append("%s = %d" % (key, cls._inf.get(key)))
                if verb:
                    newlist.append("%s.__dsc__ = %s" % (key, cls._dsc.get(key)))

            return newlist

    @classmethod
    def dsc(cls, name, dsc):
        cls._dsc[name] = dsc

    @classmethod
    def rem(cls, name):
        if name in cls._inf:
            del cls._inf[name]

    @classmethod
    def get(cls, name):
        cls._inf.get(name, 0)

    @classmethod
    @locktan()
    def set(cls, name, val=1):
        cls._inf[name] = int(val)

    @classmethod
    @locktan()
    def clr(cls, name):
        cls._inf[name] = 0

    @classmethod
    @locktan()
    def inc(cls, name, inc=1):
        cls._inf[name] = cls._inf.get(name, 0) + int(inc)

    @classmethod
    @locktan()
    def dec(cls, name, dec=1):
        cls._inf[name] = cls._inf.get(name, 0) - int(dec)

    @classmethod
    def lnkfun(cls, name, fun, args=None):
        cls._fun[name] = [fun, args]

    @classmethod
    def refcall(cls, name, inc=1):
        def realcall(*args, **kwargs):
            cls.inc(name, inc)
            pass
        return realcall
kstat = KStat

class KStatOne(object):
    def __init__(self, name, dsc=None):
        self.name = name
        if dsc:
            KStat.dsc(self.name, dsc)

    def dmp(self):
        return {self.name: KStat.dmp(self.name)}

    def dsc(self, dsc):
        return KStat.dsc(self.name, dsc)

    def rem(self):
        return KStat.rem(self.name)

    def get(self):
        return KStat.get(self.name)

    def set(self, val=1):
        return KStat.set(self.name, val)

    def clr(self):
        return KStat.clr(self.name)

    def inc(self, inc=1):
        return KStat.inc(self.name, inc)

    def dec(self, dec=1):
        return KStat.dec(self.name, dec)

    def lnkfun(self, fun, args=None):
        return KStat.lnkfun(self.name, fun, args)

    def refcall(self, inc=1):
        return KStat.refcall(self.name, inc)

kstatone = KStatOne
