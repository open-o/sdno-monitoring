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

from xlogger import *


class MyLogger(object):

    def __init__(self, conf):
        self.conf = conf
        self.conf.setmonitor(self.cfg_changed)

        self.cfg_stdout = 0
        self.cfg_stderr = 0
        self.cfg_file = None
        self.cfg_network = None

        self.cfg_changed(None)

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
            traceback.print_exc()

        try:
            if self.cfg_stderr != cfg_stderr:
                klog.to_stderr(enable=cfg_stderr)
                self.cfg_stderr = cfg_stderr
        except:
            traceback.print_exc()

        try:
            if self.cfg_file != cfg_file:
                if self.cfg_file:
                    klog.to_file(enable=False)

                if cfg_file:
                    pathfmt, size, time, when = cfg_file.split()
                    klog.to_file(
                        pathfmt=pathfmt,
                        size=size_parse(size),
                        time=int(time),
                        when=int(when))
                else:
                    klog.to_file(enable=False)
                self.cfg_file = cfg_file
        except:
            traceback.print_exc()

        try:
            if self.cfg_network != cfg_network:
                if self.cfg_network:
                    klog.to_network(enable=False)

                if cfg_network:
                    addr, port = cfg_network.split()
                    klog.to_network(addr=addr, port=int(port))
                self.cfg_network = cfg_network
        except:
            traceback.print_exc()
