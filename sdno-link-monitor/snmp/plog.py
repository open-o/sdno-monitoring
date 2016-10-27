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


import os
import sys
import ctypes
import traceback
import datetime
from bprint import cp


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

    _to_stderr = False
    _to_stdout = True
    _to_file = False
    _to_network = False

    @classmethod
    def to_stderr(cls, enable=True):
        cls._to_stderr = enable

    @classmethod
    def to_stdout(cls, enable=True):
        cls._to_stdout = enable

    @classmethod
    def to_file(
            cls,
            pathfmt="/tmp/klog-%N%Y%R_%S%F%M-%U-%P-%I.log",
            size=0,
            time=0,
            when=0,
            enable=True):

        cls._to_file = enable

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
    def _log(cls, indi, mask, *str_segs):
        now = datetime.datetime.now()

        frame = sys._getframe(2)
        _x_ln = frame.f_lineno
        _x_fn = frame.f_code.co_filename
        _x_func = frame.f_code.co_name

        ts = "%s.%03d" % (now.strftime("%Y/%m/%d %H:%M:%S"), now.microsecond / 1000)

        fullstr = ""
        for seg in str_segs:
            try:
                s = str(seg)
            except:
                try:
                    s = unicode(seg)
                except:
                    s = seg.encode("utf-8")
            fullstr += s

        line = "|%s|%s|%s|%s|%s| %s\n" % (cp.r(indi), cp.y(ts),
                _x_fn, cp.c(_x_func), cp.c(_x_ln), fullstr)

        if cls._to_stderr:
            sys.stderr.write(line)

        if cls._to_stdout:
            sys.stdout.write(line)
            sys.stdout.flush()

        if cls._to_file:
            sys.logfile.write(line)
            sys.logfile.flush()

        if cls._to_network:
            pass

    @classmethod
    def fatal(cls, *str_segs):
        KLog._log('F', cls.KLOG_FATAL, *str_segs)

    @classmethod
    def alert(cls, *str_segs):
        KLog._log('A', cls.KLOG_ALERT, *str_segs)

    @classmethod
    def critical(cls, *str_segs):
        KLog._log('C', cls.KLOG_CRIT, *str_segs)

    @classmethod
    def error(cls, *str_segs):
        KLog._log('E', cls.KLOG_ERR, *str_segs)

    @classmethod
    def warning(cls, *str_segs):
        KLog._log('W', cls.KLOG_WARNING, *str_segs)

    @classmethod
    def info(cls, *str_segs):
        KLog._log('I', cls.KLOG_INFO, *str_segs)

    @classmethod
    def notice(cls, *str_segs):
        KLog._log('N', cls.KLOG_NOTICE, *str_segs)

    @classmethod
    def debug(cls, *str_segs):
        KLog._log('D', cls.KLOG_DEBUG, *str_segs)


klog = KLog
klog.f = KLog.fatal
klog.a = KLog.alert
klog.c = KLog.critical
klog.e = KLog.error
klog.w = KLog.warning
klog.i = KLog.info
klog.n = KLog.notice
klog.d = KLog.debug
