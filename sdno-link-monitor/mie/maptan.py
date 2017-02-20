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


class MapTan():
    def __init__(self, hashkey=None):
        self._dic = {}
        self._hashfun = hashkey or self._def_hashkey

    def _def_hashkey(self, *args):
        return "DEF_HASH_KEY"

    def _hashfun(self, *args):
        hashfun = self.hashkey if hasattr(self, "hashkey") else self._hashfun
        return hashfun(*args)

    def clr(self):
        self._dic = {}

    def has(self, *args):
        hashkey = self._hashfun(*args)
        return hashkey in self._dic

    def get(self, *args):
        hashkey = self._hashfun(*args)
        return self._dic.get(hashkey)

    def set(self, obj, *args):
        hashkey = self._hashfun(*args)
        self._dic[hashkey] = obj

    def rem(self, obj, *args):
        hashkey = self._hashfun(*args)
        del self._dic[hashkey]

    def len(self):
        return len(self._dic)

    def walk(self, func):
        for k, v in self._dic.items():
            func(k, v)
