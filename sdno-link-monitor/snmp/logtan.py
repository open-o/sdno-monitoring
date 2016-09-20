#!/usr/bin/env python
# -*- coding: utf_8 -*-
#
#  Copyright (c) 2016, China Telecommunication Co., Ltd.
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


class LogTan():
    __metaclass__ = ClsSingleton

    def __init__(self, dbname="logtan"):
        self.client = pymongo.MongoClient()
        self.db = self.client[dbname]

        conf = {"capped": True, "size": 1000000, "max": 4096}
        # XXX: self.db.create_collection("activity", conf)
        self.log = self.db.activity

    def add(self, msg, type=None, modu=None):
        type = type or "info"
        modu = modu or "unkown"

        dic = {
            "ts": datetime.datetime.now(),
            "type": type,
            "modu": modu,
            "msg": msg
        }
        self.log.insert(dic)

    def i(self, msg, modu=None):
        return self.add(msg, "info", modu)

    def w(self, msg, modu=None):
        return self.add(msg, "warn", modu)

    def e(self, msg, modu=None):
        return self.add(msg, "error", modu)

    def f(self, msg, modu=None):
        return self.add(msg, "fatal", modu)

logtan = LogTan()
