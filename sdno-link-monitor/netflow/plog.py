#!/usr/bin/python
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


import os
import sys
import ctypes
import traceback
import datetime


class KLog(object):
    #
    # Const
    #
    KLOG_FATAL = ctypes.c_uint(0x00000001)
    KLOG_ALERT = ctypes.c_uint(0x00000002)
    KLOG_CRIT = ctypes.c_uint(0x00000004)
    KLOG_ERR = ctypes.c_uint(0x00000008)
    KLOG_WARNING = ctypes.c_uint(0x00000010)
    KLOG_NOTICE = ctypes.c_uint(0x00000020)
    KLOG_INFO = ctypes.c_uint(0x00000040)
    KLOG_DEBUG = ctypes.c_uint(0x00000080)

    filepath = "/dev/stdout"

    @classmethod
    def to_stderr(cls, enable=True):
        pass

    @classmethod
    def to_stdout(cls, enable=True):
        pass

    @classmethod
    def to_file(
            cls,
            pathfmt="/tmp/klog-%N%Y%R_%S%F%M-%U-%P-%I.log",
            size=0,
            time=0,
            when=0,
            enable=True):

        now = datetime.datetime.now()
        path = pathfmt
        path = path.replace("%N", "%04d" % (now.year))
        path = path.replace("%Y", "%02d" % (now.month))
        path = path.replace("%R", "%02d" % (now.day))
        path = path.replace("%S", "%02d" % (now.hour))
        path = path.replace("%F", "%02d" % (now.minute))
        path = path.replace("%M", "%02d" % (now.second))
        path = path.replace("%I", "0000")
        path = path.replace("%U", os.environ.get("USER"))

        cls.filepath = path
        cls.logfile = open(cls.filepath, "a")

    @classmethod
    def to_network(cls, addr="127.0.0.1", port=7777, enable=True):
        pass

    def __init__(self, frame):
        pass

    def check(self, mask):
        pass

    @classmethod
    def getinf(cls, frame, fn, ln):
        pass

    @classmethod
    def _log(cls, indi, mask, s, nl):
        now = datetime.datetime.now()
        line = "|%s|%s.%d|%s\n" % (indi, now.strftime(
            "%Y/%m/%d %H:%M:%S"), now.microsecond / 1000, s)
        cls.logfile.write(line)
        cls.logfile.flush()

    @classmethod
    def fatal(cls, s="", nl=True):
        KLog._log('F', cls.KLOG_FATAL, s, nl)

    @classmethod
    def alert(cls, s="", nl=True):
        KLog._log('A', cls.KLOG_ALERT, s, nl)

    @classmethod
    def critical(cls, s="", nl=True):
        KLog._log('C', cls.KLOG_CRIT, s, nl)

    @classmethod
    def error(cls, s="", nl=True):
        KLog._log('E', cls.KLOG_ERR, s, nl)

    @classmethod
    def warning(cls, s="", nl=True):
        KLog._log('W', cls.KLOG_WARNING, s, nl)

    @classmethod
    def info(cls, s="", nl=True):
        KLog._log('I', cls.KLOG_INFO, s, nl)

    @classmethod
    def notice(cls, s="", nl=True):
        KLog._log('N', cls.KLOG_NOTICE, s, nl)

    @classmethod
    def debug(cls, s="", nl=True):
        KLog._log('D', cls.KLOG_DEBUG, s, nl)


klog = KLog
klog.f = KLog.fatal
klog.a = KLog.alert
klog.c = KLog.critical
klog.e = KLog.error
klog.w = KLog.warning
klog.i = KLog.info
klog.n = KLog.notice
klog.d = KLog.debug
