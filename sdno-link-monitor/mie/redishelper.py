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

### ###########################################################
# RedisDB
#
import redis


class RedisDB(object):

    def __init__(self, conf, hostconf, portconf, dbconf):
        self.db = None
        self.host = None
        self.port = None
        self.dbindex = None

        self.hostkey, self.hostval = hostconf
        self.portkey, self.portval = portconf
        self.dbkey, self.dbval = dbconf

        self.conf = conf
        self.conf.setmonitor(self.cfg_changed)
        self.cfg_changed()

    def cfg_changed(self, cookie=None):
        host = self.conf.xget(self.hostkey, self.hostval)
        port = self.conf.xget(self.portkey, self.portval)
        dbindex = self.conf.xget(self.dbkey, self.dbval)

        if not self.db or host != self.host or port != self.port or dbindex != self.dbindex:
            self.db = redis.Redis(host=host, port=port, db=dbindex)
            self.host = host
            self.port = port
            self.dbindex = dbindex


class RedisBatch(object):
    '''rbat host port dbindex 'commanda arga argb ... argn' ' commandb ...' '''

    def __init__(self, host, port, dbindex):
        self.host = host
        self.port = port
        self.dbindex = dbindex

    def __call__(self, cmds, contimode=False):
        self.db = redis.Redis(host=self.host, port=self.port, db=self.dbindex)

        results = []
        for cmd in cmds:
            print "CMD:", cmd
            try:
                result = self.db.execute_command(*cmd)
                results.append(result)
            except:
                results.append(None)
                klog.e("Except: cmd: '%s'" % cmd)
                klog.e("%s" % traceback.format_exc())
                if contimode:
                    continue
                break

        return results
