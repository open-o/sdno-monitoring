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


from xlogger import klog


class KLogMon(object):

    def __init__(self, conf):
        self.conf = conf
        self.conf.setmonitor(self.cfg_changed)

        self.cfg_stdout = 0
        self.cfg_stderr = 0
        self.cfg_file = None
        self.cfg_network = None

        self.cfg_changed(None)

    def size_parse(self, size):
        if not size:
            return 0

        size = size.strip()

        if size[-1] in 'kK':
            size = int(size[:-1]) * 1024
        elif size[-1] in 'mM':
            size = int(size[:-1]) * 1024 * 1024
        elif size[-1] in 'gG':
            size = int(size[:-1]) * 1024 * 1024 * 1024
        elif size[-1] in 'tT':
            size = int(size[:-1]) * 1024 * 1024 * 1024 * 1024
        elif size[-1] in 'pP':
            size = int(size[:-1]) * 1024 * 1024 * 1024 * 1024 * 1024
        else:
            size = int(size)

        return size

    def cfg_changed(self, cookie):
        cfg_stdout = self.conf.xget("log/stdout", 1)
        cfg_stderr = self.conf.xget("log/stderr", 0)
        cfg_file = self.conf.xget("log/file", "")
        cfg_network = self.conf.xget("log/network", "")

        try:
            if self.cfg_stdout != cfg_stdout:
                klog.to_stdout(enable=cfg_stdout)
                self.cfg_stdout = cfg_stdout
        except:
            pass

        try:
            if self.cfg_stderr != cfg_stderr:
                klog.to_stderr(enable=cfg_stderr)
                self.cfg_stderr = cfg_stderr
        except:
            pass

        try:
            if self.cfg_file != cfg_file:
                if self.cfg_file:
                    klog.to_file(enable=False)

                if cfg_file:
                    pathfmt, size, time, when = cfg_file.split()
                    klog.to_file(
                        pathfmt=pathfmt,
                        size=self.size_parse(size),
                        time=int(time),
                        when=int(when))
                else:
                    klog.to_file(enable=False)
                self.cfg_file = cfg_file
        except:
            pass

        try:
            if self.cfg_network != cfg_network:
                if self.cfg_network:
                    klog.to_network(enable=False)

                if cfg_network:
                    addr, port = cfg_network.split(":")
                    klog.to_network(addr=addr, port=int(port))
                self.cfg_network = cfg_network
        except:
            pass
