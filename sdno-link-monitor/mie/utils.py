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
