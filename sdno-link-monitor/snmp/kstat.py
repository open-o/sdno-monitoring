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

import re
from locktan import locktan

### ###########################################################
# Statistic Information
#


class KStat(object):
    _inf = {}
    _fun = {}

    @classmethod
    def dump(cls, what=None):
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

        l = []
        for k, v in d.items():
            res = pat.search(k)
            if res:
                l.append("%s=%s" % (k, str(v)))
        l.sort(lambda a, b: cmp(a[2:], b[2:]))

        newlist = []
        oldgroup = ""
        for tmp in l:
            try:
                groups = tmp.split(".")
                if not groups:
                    continue
                group = groups[0]
                if oldgroup != group:
                    newlist.append("")
                    oldgroup = group
            except:
                pass
            newlist.append(tmp.strip())

        return newlist[1:]

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
        cls._inf[name] = val

    @classmethod
    @locktan()
    def inc(cls, name, inc=1):
        cls._inf[name] = cls._inf.get(name, 0) + inc

    @classmethod
    @locktan()
    def dec(cls, name, dec=1):
        cls._inf[name] = cls._inf.get(name, 0) - dec

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
