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


import os
import sys
import ctypes
import traceback


def get_settings():
    #
    # --klog-dfcfg=xxx
    # --klog-rtcfg=xxx
    # --klog-mask=xxx
    #
    # command line > environment
    #

    dfcfg, rtcfg, mask = None, None, None
    for argv in sys.argv:
        if argv.startswith("--klog-dfcfg="):
            dfcfg = argv[13:]

        if argv.startswith("--klog-rtcfg="):
            rtcfg = argv[13:]

        if argv.startswith("--klog-mask="):
            mask = argv[12:]

    if dfcfg is None:
        dfcfg = os.environ.get("KLOG_DFCFG")

    if rtcfg is None:
        rtcfg = os.environ.get("KLOG_RTCFG")

    if mask is None:
        mask = os.environ.get("KLOG_MASK")

    return dfcfg, rtcfg, mask


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
    KLOG_TYPE_ALL = ctypes.c_uint(0x000000ff)

    KLOG_RTM = ctypes.c_uint(0x00000100)
    KLOG_ATM = ctypes.c_uint(0x00000200)

    KLOG_PID = ctypes.c_uint(0x00001000)
    KLOG_TID = ctypes.c_uint(0x00002000)

    KLOG_PROG = ctypes.c_uint(0x00010000)
    KLOG_MODU = ctypes.c_uint(0x00020000)
    KLOG_FILE = ctypes.c_uint(0x00040000)
    KLOG_FUNC = ctypes.c_uint(0x00080000)
    KLOG_LINE = ctypes.c_uint(0x00100000)

    klogloc = {}

    #
    # Configure for me
    #

    #
    # Load the API
    #
    hilda = ctypes.CDLL("libhilda.so")

    NLOGGER = ctypes.CFUNCTYPE(None, ctypes.c_char_p, ctypes.c_int)

    klog_init = hilda.klog_init
    klog_init.argtypes = [ctypes.c_int, ctypes.c_void_p]
    klog_init.restype = ctypes.c_void_p

    klog_touches = hilda.klog_touches
    klog_touches.argtypes = None
    klog_touches.restype = ctypes.c_int

    klog_add_logger = hilda.klog_add_logger
    klog_add_logger.argtypes = [ctypes.c_void_p]
    klog_add_logger.restype = None

    klog_calc_mask = hilda.klog_calc_mask
    klog_calc_mask.argtypes = [
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_int]
    klog_calc_mask.restype = ctypes.c_uint

    klog_file_name_add = hilda.klog_file_name_add
    klog_file_name_add.argtypes = [ctypes.c_char_p]
    klog_file_name_add.restype = ctypes.c_void_p

    klog_func_name_add = hilda.klog_func_name_add
    klog_func_name_add.argtypes = [ctypes.c_char_p]
    klog_func_name_add.restype = ctypes.c_void_p

    klog_modu_name_add = hilda.klog_modu_name_add
    klog_modu_name_add.argtypes = [ctypes.c_char_p]
    klog_modu_name_add.restype = ctypes.c_void_p

    klog_prog_name_add = hilda.klog_prog_name_add
    klog_prog_name_add.argtypes = [ctypes.c_char_p]
    klog_prog_name_add.restype = ctypes.c_void_p

    klog_f = hilda.klog_f
    klog_f.argtypes = [
        ctypes.c_uint8,
        ctypes.c_uint,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_int,
        ctypes.c_char_p]
    klog_f.restype = ctypes.c_int

    klog_set_default_mask = hilda.klog_set_default_mask
    klog_set_default_mask.argtypes = [ctypes.c_uint]
    klog_set_default_mask.restype = None

    #
    # Builtin logger
    #

    # logger: stdout
    klog_add_stdout_logger = hilda.klog_add_stdout_logger
    klog_add_stdout_logger.argtypes = None
    klog_add_stdout_logger.restype = None

    klog_del_stdout_logger = hilda.klog_del_stdout_logger
    klog_del_stdout_logger.argtypes = None
    klog_del_stdout_logger.restype = None

    # logger: stderr
    klog_add_stderr_logger = hilda.klog_add_stderr_logger
    klog_add_stderr_logger.argtypes = None
    klog_add_stderr_logger.restype = None

    klog_del_stderr_logger = hilda.klog_del_stderr_logger
    klog_del_stderr_logger.argtypes = None
    klog_del_stderr_logger.restype = None

    # logger: file
    klog_add_file_logger = hilda.klog_add_file_logger
    klog_add_file_logger.argtypes = [
        ctypes.c_char_p,
        ctypes.c_uint,
        ctypes.c_uint,
        ctypes.c_uint]
    klog_add_file_logger.restype = None

    klog_del_file_logger = hilda.klog_del_file_logger
    klog_del_file_logger.argtypes = None
    klog_del_file_logger.restype = None

    # logger: network
    klog_add_network_logger = hilda.klog_add_network_logger
    klog_add_network_logger.argtypes = [ctypes.c_char_p, ctypes.c_uint16]
    klog_add_network_logger.restype = None

    klog_del_network_logger = hilda.klog_del_network_logger
    klog_del_network_logger.argtypes = None
    klog_del_network_logger.restype = None

    #
    # Let's go
    #

    dfcfg, rtcfg, mask = get_settings()

    if dfcfg:
        os.environ["KLOG_DFCFG"] = dfcfg

    if rtcfg:
        os.environ["KLOG_RTCFG"] = rtcfg

    cmask = 0
    if mask is not None:
        # facewind sS xj PMFHN
        dic = {
            'f': KLOG_FATAL,
            'a': KLOG_ALERT,
            'c': KLOG_CRIT,
            'e': KLOG_ERR,
            'w': KLOG_WARNING,
            'n': KLOG_NOTICE,
            'i': KLOG_INFO,
            'd': KLOG_DEBUG,

            's': KLOG_RTM,
            'S': KLOG_ATM,

            'j': KLOG_PID,
            'x': KLOG_TID,

            'P': KLOG_PROG,
            'M': KLOG_MODU,
            'F': KLOG_FILE,
            'H': KLOG_FUNC,
            'N': KLOG_LINE,
        }

        for c in mask:
            m = dic.get(c, 0)
            cmask |= m.value
    else:
        cmask = KLOG_TYPE_ALL.value | KLOG_ATM.value | KLOG_FILE.value | KLOG_FUNC.value | KLOG_LINE.value

    klog_set_default_mask(cmask)

    klog_init(0, None)

    @classmethod
    def to_stderr(cls, enable=True):
        if enable:
            cls.klog_add_stderr_logger()
        else:
            cls.klog_del_stderr_logger()

    @classmethod
    def to_stdout(cls, enable=True):
        if enable:
            cls.klog_add_stdout_logger()
        else:
            cls.klog_del_stdout_logger()

    @classmethod
    def to_file(
            cls,
            pathfmt="/tmp/klog-%N%Y%R_%S%F%M-%U-%P-%I.log",
            size=0,
            time=0,
            when=0,
            enable=True):
        if enable:
            cls.klog_add_file_logger(pathfmt, size, time, when)
        else:
            cls.klog_del_file_logger()

    @classmethod
    def to_network(cls, addr="127.0.0.1", port=7777, enable=True):
        if enable:
            cls.klog_add_network_logger(addr, port)
        else:
            cls.klog_del_network_logger()

    def __init__(self, frame):
        self._touches = -8
        self._mask = None

        _file = os.path.basename(frame.f_code.co_filename)

        self._prog = KLog.klog_prog_name_add(None)
        self._modu = KLog.klog_modu_name_add("MIE")
        self._file = KLog.klog_file_name_add(_file)
        self._func = KLog.klog_func_name_add(frame.f_code.co_name)
        self._line = frame.f_lineno

    def check(self, mask):
        touches = KLog.klog_touches()
        if self._touches != touches:
            self._touches = touches

            calced_mask = KLog.klog_calc_mask(
                self._prog, self._modu, self._file, self._func, self._line)

            if calced_mask & mask.value:
                self._mask = calced_mask
            else:
                self._mask = 0

    @classmethod
    def getinf(cls, frame, fn, ln):
        locid = "%s@%d" % (fn, ln)
        logInf = cls.klogloc.get(locid)
        if not logInf:
            logInf = KLog(frame)
            cls.klogloc[locid] = logInf
        return logInf

    @classmethod
    def _log(cls, indi, mask, nl, *str_segs):
        try:
            frame = sys._getframe(2)
            _x_ln = frame.f_lineno
            _x_fn = frame.f_code.co_filename

            inf = cls.getinf(frame, _x_fn, _x_ln)
            inf.check(mask)
            if inf._mask:
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

                if nl:
                    cls.klog_f(
                        ctypes.c_uint8(ord(indi)),
                        inf._mask,
                        inf._prog,
                        inf._modu,
                        inf._file,
                        inf._func,
                        inf._line,
                        "%s\r\n",
                        fullstr)
                else:
                    cls.klog_f(
                        ctypes.c_uint8(ord(indi)),
                        inf._mask,
                        inf._prog,
                        inf._modu,
                        inf._file,
                        inf._func,
                        inf._line,
                        "%s",
                        fullstr)
        except:
            print("Exception: '%s'" % fullstr)
            print("Exception: '%s'" % type(fullstr))
            traceback.print_exc()

    @classmethod
    def f(cls, *str_segs):
        '''fatal'''
        KLog._log('F', cls.KLOG_FATAL, True, *str_segs)

    @classmethod
    def a(cls, *str_segs):
        '''alert'''
        KLog._log('A', cls.KLOG_ALERT, True, *str_segs)

    @classmethod
    def c(cls, *str_segs):
        '''critical'''
        KLog._log('C', cls.KLOG_CRIT, True, *str_segs)

    @classmethod
    def e(cls, *str_segs):
        '''error'''
        KLog._log('E', cls.KLOG_ERR, True, *str_segs)

    @classmethod
    def w(cls, *str_segs):
        '''warning'''
        KLog._log('W', cls.KLOG_WARNING, True, *str_segs)

    @classmethod
    def i(cls, *str_segs):
        '''info'''
        KLog._log('I', cls.KLOG_INFO, True, *str_segs)

    @classmethod
    def n(cls, *str_segs):
        '''notice'''
        KLog._log('N', cls.KLOG_NOTICE, True, *str_segs)

    @classmethod
    def d(cls, *str_segs):
        '''debug'''
        KLog._log('D', cls.KLOG_DEBUG, True, *str_segs)


klog = KLog
