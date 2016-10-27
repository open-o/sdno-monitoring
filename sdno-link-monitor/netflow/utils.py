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


import re
import os
import sys
import time
import threading
import traceback
import socket
import random
import shlex

from functools import reduce

import subprocess

def vernumber(v):
    '''Covert version string a.b.c to a number

    a.b.c => 1.2.3 => a * 10000 * 10000 + b * 10000 + c
    '''
    count = v.count(".")
    a, b, c = "0", "0", "0"

    try:
        if count == 3:
            a, b, c = v.split(".")
        elif count == 2:
            a, b = v.split(".")
        elif count == 1:
            a = v
    except:
        print "BAD VERSION <%s>" % v

    return int(a) * 10000 * 10000 + int(b) * 10000 + int(c)


def ipaddr():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 0))
        ip = s.getsockname()[0]
        s.close()
    except:
        ip = "127.0.0.1"
    return ip


def rands(seed, length):
    return ''.join([seed[x]
                    for x in random.sample(xrange(0, len(seed)), length)])


def randobj(obj):
    weight_all = sum([seg[1] for seg in obj])

    randnum = random.random()
    randnum = randnum * weight_all

    w_start = 0.0
    w_end = 1.0
    index = 0
    for seg in obj:
        w_cur = float(seg[1])
        w_end = w_start + w_cur

        if w_start <= randnum <= w_end:
            return obj[index][0]

        w_start = w_end
        index += 1
    else:
        def null():
            return ""
        return null


def hexdump(s):
    return ":".join("{:02x}".format(ord(c)) for c in s)


def size_parse(size):
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

### ###########################################################
# timer
#


def now_sec():
    return time.time()


def now_msec():
    return time.time() * 1000


def now_usec():
    return time.time() * 1000 * 1000


def now_str():
    return time.strftime("%Y-%m-%d %H:%M:%S")


def now_str_2():
    return time.strftime("%Y%m%d%H%M%S")




def extname(s):
    if not s:
        return None

    start = s.rfind(".") + 1
    if start < 1 or start == len(s):
        return None

    return s[start:]



### ###########################################################
# System information
#
# directly use platform.xxx()



### ###########################################################
# setdebugable
#
# kill -USR1 <python_application.pid>
def setdebugable():
    import signal

    def handle_pdb(sig, frame):
        import pdb
        pdb.Pdb().set_trace(frame)
    signal.signal(signal.SIGUSR1, handle_pdb)



### ###########################################################
# Quitmarker
#
def quitmarker(markerfile=None):
    markerfile = markerfile or "/tmp/mie/quitmarker"
    g = frame(-1).f_globals
    g["quitmarker"] = open(markerfile, 'r')



### ###########################################################
# Jobs
#
class CmdJobs(object):
    _jobid = 0

    @classmethod
    def jid(cls):
        res = cls._jobid
        cls._jobid += 1
        if not res:
            res = cls._jobid
            cls._jobid += 1
        return res

    def __init__(self):
        # jid
        self.jobs = {}

    def addjob(self):
        job = self.jid()
        pass

# 1. call a command to start a job
# 2. report a event to server

# >>> job_set/get/del

# >>> jobset


### #####################################################################
# Helper.py
#
class CallSerialNumber(object):
    call_serial_number = 0

    @classmethod
    def csn(cls):
        sn = cls.call_serial_number
        cls.call_serial_number += 1
        if not sn:
            sn = cls.call_serial_number
            cls.call_serial_number += 1
        return sn

csngen = CallSerialNumber


class InstanceID(object):
    instanceID = None

    @classmethod
    def iid(cls):
        if cls.instanceID is None:
            def method_iidfile():
                f = None
                try:
                    f = open("/tmp/.mie.iid", "r")
                    x = f.readline()
                    x = int(x)
                except:
                    x = 0
                finally:
                    if f:
                        f.close()

                f = None
                try:
                    f = open("/tmp/.mie.iid", "w")
                    f.write("%s " % (x + 1))
                    f.close()
                except:
                    pass
                finally:
                    if f:
                        f.close()

                try:
                    a, b, c, d = map(lambda x: int(x), s.split("."))
                    y = a * 255 * 255 * 255
                    y += b * 255 * 255
                    y += c * 255
                    y += d
                except:
                    y = 1122

                z = int("%d%d" % (y, x)) ^ 0x4d6f5965
                z = "M" + hex(z)[2:][::-1]
                return z

            def method_hash():
                import string
                import hashlib
                seed = "%s:%f:%s" % (ipaddr(), time.time(),
                                     rands(string.ascii_letters, 4))
                return hashlib.md5(seed).hexdigest()[:6]

            def method_rand():
                return rands(string.ascii_letters, 4)

            def method_fix():
                a, b, c, d = map(lambda x: int(x), ipaddr().split("."))

                iid = os.environ.get("MIE_IID")
                if iid:
                    return iid

                iidpre = os.environ.get("MIE_IID_PREFIX")
                if not iidpre:
                    script = os.path.basename(sys.argv[0])
                    iidpre = os.path.splitext(script)[0]

                return "%s_%03d_%03d_%03d_%03d" % (iidpre.upper(), a, b, c, d)

            cls.instanceID = method_fix()
        return cls.instanceID

iidgen = InstanceID

### #####################################################################
# calulate MD5 for a given file path
#

def md5_file(path):
    md5 = hashlib.md5()
    f = open(path_local, "rb")
    while True:
        data = f.read(4096)
        if not data:
            break
        md5.update(data)
    chkmd5 = md5.hexdigest()
    f.close()
    return chkmd5

### ###########################################################
# System information
#

class DeferDo(threading.Thread):
    def __init__(self, defer, cookie=None):
        threading.Thread.__init__(self)
        self.defer = defer
        self.cookie = cookie
        self.start()

    def run(self):
        self.defer(self.cookie)


### ###########################################################
# Logger monitor configure
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


### ###########################################################
# Get object by id
#
def objbyid(ID):
    import ctypes
    return ctypes.cast(ID, ctypes.py_object).value


### ###########################################################
# Process functions
#


def pidof(name):
    return subprocess.check_output(['pidof', name])


def pkill_by_name(name):
    pid = subprocess.check_output(['pidof', name])
    if pid:
        subprocess.check_output(['kill', pid])

    pid = subprocess.check_output(['pidof', name])
    if pid:
        subprocess.check_output(['kill', '-9', pid])

    pid = subprocess.check_output(['pidof', name])
    if pid:
        return False

    return True


def pkill_by_pid(pid):
    subprocess.call(['kill', pid])
    subprocess.call(['kill', '-9', pid])


def pexec(name, args, force=False, nohup=True):
    if force:
        if not pkill_by_name(name):
            return False

    pid = subprocess.check_output(['pidof', name])
    if pid:
        return True

    appname = os.path.basename(args[1])

    if nohup:
        args.insert("nohup")
    subprocess.check_output(args)

    pid = subprocess.check_output(['pidof', appname])
    if pid:
        return True

    return False


def pgrep(*args):
    cmd = "ps f | "

    if not args:
        return ""

    for arg in args:
        cmd += "grep %s | " % arg

    cmd += "grep -v grep | head -n 1 | awk '{print $1}' | xargs kill"
    print cmd

    stdout = subprocess.PIPE
    stderr = subprocess.STDOUT
    ps = subprocess.Popen(cmd, shell=True, stdout=stdout, stderr=stderr)
    return ps.communicate()[0]


def strbt():
    stack = traceback.format_stack()
    return "\r\n".join(stack[:-1])

from collections import defaultdict

def tree():
    return defaultdict(tree)

### ###########################################################
# Play with json command package
#

class DotDict(dict):
    def __init__(self, **kwargs):
        dict.update(self, kwargs)

    def __getattr__(self, k):
        return self.get(k, None)

    def __setattr__(self, k, v):
        self[k] = v

Obj = DotDict



### ###########################################################
# Socket
#
def sockget(s, length):
    dat = ""
    left = length
    while left:
        try:
            tmp = s.recv(left)
        except socket.error as err:
            if err.errno == 11:
                continue
            raise
        except:
            raise

        if not tmp:
            return None
        left -= len(tmp)
        dat += tmp
    return dat




class WBList():
    '''White List and Black List'''

    def __init__(self):
        self.wlist = {}
        self.blist = {}

    def wset(self, name):
        self.wlist[name] = re.compile("^%s$" % name)

    def wdel(self, name=None):
        if name:
            del self.wlist[name]
        else:
            self.wlist.clear()

    def whas(self, name=None):
        pass

    def wdmp(self, name=None):
        pass
