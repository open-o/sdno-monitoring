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


class DotDict(dict):
    def _process_list(self, lis):
        l = []
        for i in lis:
            if isinstance(i, dict):
                l.append(DotDict(i))
            else:
                l.append(i)
        return l

    def __dict__(self):
        return self.todic()

    def todic(self):
        d = {}
        for k, v in self.items():
            if type(v) is DotDict:
                if id(v) == id(self):
                    v = d
                else:
                    v = v.todic()
            elif type(v) is list:
                l = []
                for i in v:
                    n = i
                    if type(i) is DotDict:
                        n = i.todic()
                    l.append(n)
                v = l
            d[k] = v
        return d

    def frdic(self, dic):
        for k, v in dic.items():
            if isinstance(v, dict):
                v = DotDict(v)
            elif isinstance(v, list):
                v = self._process_list(v)
            elif isinstance(v, tuple):
                v = tuple(self._process_list(v))

            if type(v) == "dict":
                print("ERROR! Should not be dict: '%s'" % v)
            self[k] = v
        pass

    def frtup(self, tup):
        if not isinstance(tup[0], dict):
            print("ERROR! tup[0] is %s, dict wanted" % type(tup[0]))
            return
        return self.frdic(tup[0])

    def __init__(self, *args, **kwargs):
        if args:
            return self.frtup(args)

        if kwargs:
            return self.frdic(kwargs)

    def __getattr__(self, k):
        v = self.get(k, DotDict())
        self[k] = v
        return v

    def __setattr__(self, k, v):
        self[k] = v

    def __dir__(self):
        return self.keys()
