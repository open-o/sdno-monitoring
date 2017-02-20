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

from singleton import ClsSingleton
import pymongo
import datetime


class LogTan_MongoDB():
    __metaclass__ = ClsSingleton
    _client = None

    @classmethod
    def cfg(cls, **kwargs):
        cls._client = pymongo.MongoClient()

        cls._db = cls._client[kwargs.get("db", "logtan")]
        cls._size = int(kwargs.get("size", "1000000"))
        cls._max = int(kwargs.get("max", "4096"))

        conf = {"capped": True, "size": cls._size, "max": cls._max}
        try:
            cls._db.create_collection("activity", conf)
        except:
            pass
        cls._log = cls._db.activity

    def add(cls, rec, lvl=None, mod=None):
        lvl = lvl or "II"
        mod = mod or "unknown"

        if not cls._client:
            cls.cfg()

        dic = {
            "ts": datetime.datetime.now(),
            "lvl": lvl,
            "mod": mod,
            "rec": rec
        }
        cls._log.insert(dic)

    def i(cls, rec, mod=None):
        # Info
        cls.add(rec, "II", mod)

    def w(cls, rec, mod=None):
        # Warn
        cls.add(rec, "WW", mod)

    def e(cls, rec, mod=None):
        # Error
        cls.add(rec, "EE", mod)

    def f(cls, rec, mod=None):
        # Fatal
        cls.add(rec, "FF", mod)

logtan = LogTan_MongoDB()


def cfg(**kwargs):
    '''logtan.cfg(db="logtan", size=1000000, max=4096)'''
    logtan.cfg(**kwargs)


def i(mod=None, **kwargs):
    logtan.i(dict(kwargs), mod)


def w(mod=None, **kwargs):
    logtan.w(dict(kwargs), mod)


def e(mod=None, **kwargs):
    logtan.e(dict(kwargs), mod)


def f(mod=None, **kwargs):
    logtan.f(dict(kwargs), mod)

