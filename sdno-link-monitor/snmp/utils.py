#!/usr/bin/env python
# -*- coding: utf_8 -*-

import re
import os
import sys
import time
import threading
import traceback
import socket
import random
import shlex
import json

import pprint
from functools import reduce


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


### ###########################################################
# Singleton: Class
#
# add ```__metaclass__ = Singleton``` in first line of class

class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(
                Singleton, cls).__call__(
                *args, **kwargs)
        return cls._instances[cls]


### ###########################################################
# Outout with color
#

class ColorPrint:
    fmt = '\033[0;3{}m{}\033[0m'.format

    BLACK = 0
    RED = 1
    GREEN = 2
    YELLOW = 3
    BLUE = 4
    PURPLE = 5
    CYAN = 6
    GRAY = 8

    @classmethod
    def black(cls, s):
        return cls.fmt(cls.BLACK, s)

    @classmethod
    def red(cls, s):
        return cls.fmt(cls.RED, s)

    @classmethod
    def green(cls, s):
        return cls.fmt(cls.GREEN, s)

    @classmethod
    def yellow(cls, s):
        return cls.fmt(cls.YELLOW, s)

    @classmethod
    def blue(cls, s):
        return cls.fmt(cls.BLUE, s)

    @classmethod
    def purple(cls, s):
        return cls.fmt(cls.PURPLE, s)

    @classmethod
    def cyan(cls, s):
        return cls.fmt(cls.CYAN, s)

    @classmethod
    def gray(cls, s):
        return cls.fmt(cls.GRAY, s)

cp = ColorPrint
cp.r = cp.red
cp.g = cp.green
cp.y = cp.yellow
cp.b = cp.blue
cp.p = cp.purple
cp.c = cp.cyan
cp.h = cp.gray


def extname(s):
    if not s:
        return None

    start = s.rfind(".") + 1
    if start < 1 or start == len(s):
        return None

    return s[start:]


### ###########################################################
# Decorator to threading lock a function
#
class locktan(object):
    lock = threading.RLock()

    def __call__(self, fn):
        def lockfn(*args, **kwargs):
            locktan.lock.acquire()
            try:
                result = fn(*args, **kwargs)
            except:
                raise
            finally:
                locktan.lock.release()
            return result
        return lockfn


### ###########################################################
# Decorator print time cost of one function
#
class timetan(object):

    def __init__(self, banner):
        self.banner = banner

    def __call__(self, fn):
        def lockfn(*args, **kwargs):
            start = time.time()
            result = fn(*args, **kwargs)
            end = time.time()
            logmsg = "%s: %f" % (cp.r("COST: %s" % self.banner), end - start)
            # print logmsg
            return result
        return lockfn


### ###########################################################
# System information
#
# directly use platform.xxx()

### ###########################################################
# Statistic Information
#
class KStat(object):
    _inf = {}
    _fun = {}

    @classmethod
    def dump(cls, what=None):
        d = {}

        if not what:
            what = ".*"

        try:
            what = ".*" + what[0] + ".*"
            pat = re.compile(what)
        except:
            pat = re.compile(".*")

        for k, v in cls._fun.items():
            d[k] = v[0](v[1])

        for k, v in cls._inf.items():
            d[k] = v

        l = []
        for k, v in d.items():
            res = pat.search(k)
            if res:
                l.append("%s=%s" % (k, str(v)))
        l.sort(lambda a, b: cmp(a[2:], b[2:]))

        newlist = []
        oldgroup = ""
        for tmp in l:
            try:
                groups = tmp.split(".")
                if not groups:
                    continue
                group = groups[0]
                if oldgroup != group:
                    newlist.append("")
                    oldgroup = group
            except:
                pass
            newlist.append(tmp.strip())

        return newlist[1:]

    @classmethod
    def rem(cls, name):
        if name in cls._inf:
            del cls._inf[name]

    @classmethod
    def get(cls, name):
        cls._inf.get(name, 0)

    @classmethod
    @locktan()
    def set(cls, name, val=1):
        cls._inf[name] = val

    @classmethod
    @locktan()
    def inc(cls, name, inc=1):
        cls._inf[name] = cls._inf.get(name, 0) + inc

    @classmethod
    @locktan()
    def dec(cls, name, dec=1):
        cls._inf[name] = cls._inf.get(name, 0) - dec

    @classmethod
    def lnkfun(cls, name, fun, args=None):
        cls._fun[name] = [fun, args]

    # TODO: refcall
    @classmethod
    def refcall(cls, name, inc=1):
        def realcall(*args, **kwargs):
            cls.inc(name, inc)
            pass
        return realcall

kstat = KStat


### ###########################################################
# Mie commands for configure
#
class MiscCommands(object):

    def __init__(self, conf, callman):
        self.conf = conf
        callman.scancmds(inst=self, prefix="docmd_", group="Misc")

    def docmd_dr(self, cmdctx, calldic):
        args = calldic.get_args()

        os.environ["DR_RTCFG"] = os.environ.get(
            "KLOG_RTCFG", "/tmp/klog.rtcfg")
        os.system("dr %s" % " ".join(args))
        return "OK"

    def docmd_stat(self, cmdctx, calldic):
        args = calldic.get_args()

        '''Show runtime stastics'''
        res = kstat.dump(args)
        return res


### ###########################################################
# Mie commands for configure
#
class ConfCommands(object):

    def __init__(self, conf, callman):
        self.conf = conf
        callman.scancmds(inst=self, prefix="docmd_", group="conf")

    def docmd_og(self, cmdctx, calldic):
        '''Return the runtime configure by given query pattern

        og <type> <pattern>
        type:u  : ???
        type:n  : ???
        type:t  : ???

        og u <redis>
        og n <redis>
        og t <redis>
        '''
        args = calldic.get_args() or []

        showtype = args[0] if len(args) > 0 else None
        pat = args[1] if len(args) > 1 else None

        return self.conf.dump(showtype, pat)

    def docmd_os(self, cmdctx, calldic):
        '''Add/Update a configure

        Usage: os key=val key=val | os key val key=val
        '''
        args = calldic.get_args() or []

        nglist = []
        segs = []
        for arg in args:
            if arg.find("=") >= 0:
                segs.extend(arg.split("=", 1))
            else:
                segs.append(arg)

        for i in range(len(segs) / 2):
            ii = i * 2
            key, val = segs[ii], segs[ii + 1]
            if not self.conf.set(key, val):
                nglist.append(key)

        return {"nglist": nglist}

    def docmd_od(self, cmdctx, calldic):
        '''Delete a configure entry'''
        args = calldic.get_args() or []

        nglist = []
        segs = []
        for arg in args:
            if not self.conf.rem(arg):
                nglist.append(arg)

        return {"nglist": nglist}

    def docmd_osave(self, cmdctx, calldic):
        '''Save the configure to file

        Usage: osave [full]
        If full set, all the configure will be saved or else
        only modified saved
        '''

        args = calldic.get_args() or []

        try:
            full = args[0].lower() == "full"
        except:
            full = False
        return "OK" if self.conf.save(full) else "NG"


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
# Get frame with depth
#
def frame(depth=-1):
    depth_all = 1
    while True:
        try:
            sys._getframe(depth_all)
            depth_all += 1
        except:
            break

    return sys._getframe((depth_all + depth) % depth_all)


### ###########################################################
# Singleton: Application
#
def singleton(pid_file, message=None):
    import fcntl

    g = frame(-1).f_globals

    fp = open(pid_file, 'w')
    g["singleton_fp"] = fp
    try:
        fcntl.lockf(fp, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except IOError:
        print message or "Another instance exist, quit now"
        sys.exit(0)


### ###########################################################
# Quitmarker
#
def quitmarker(markerfile=None):
    markerfile = markerfile or "/tmp/mie/quitmarker"
    g = frame(-1).f_globals
    g["quitmarker"] = open(markerfile, 'r')


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
import subprocess


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


### ###########################################################
# Beautiful print ...
#
class MyEnc(json.JSONEncoder):

    def default(self, o):
        try:
            it = iter(o)
        except TypeError:
            pass
        else:
            return list(it)

        try:
            return json.JSONEncoder.default(self, o)
        except TypeError:
            return str(o)


def formatb(obj, title=None, lvl=1):
    if not isinstance(obj, dict):
        if hasattr(obj, "__dict__"):
            obj = obj.__dict__

    orig = json.dumps(obj, indent=4, sort_keys=True, skipkeys=False, cls=MyEnc)
    text = eval("u'''%s'''" % orig).encode('utf-8')

    res = text

    f = sys._getframe(lvl)
    ln = f.f_lineno
    fn = f.f_code.co_filename

    if title is not None:
        title = "%s %s:%d" % (title, fn, ln)
        pre = cp.r("\r\n>>> %s\r\n" % title)
        pst = cp.r("\r\n<<< %s\r\n" % title)
        res = pre + res + pst

    return res


def printb(obj, title=None, lvl=2):
    print formatb(obj, title, lvl)


def todict(obj, classkey=None):
    if isinstance(obj, dict):
        data = {}
        for (k, v) in obj.items():
            data[k] = todict(v, classkey)
        return data
    elif hasattr(obj, "_ast"):
        return todict(obj._ast())
    elif hasattr(obj, "__iter__"):
        return [todict(v, classkey) for v in obj]
    elif hasattr(obj, "__dict__"):
        data = dict([(key, todict(value, classkey))
                     for key, value in obj.__dict__.iteritems()
                     if not callable(value) and not key.startswith('_')])
        if classkey is not None and hasattr(obj, "__class__"):
            data[classkey] = obj.__class__.__name__
        return data
    else:
        return obj


def varprt(obj, title=None):
    printb(todict(obj), title, lvl=3)


def varfmt(obj, title=None):
    return formatb(todict(obj), title, lvl=3)


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


class CallDic(DotDict):
    '''name, envs, opts, args'''

    def get_envs(self, env):
        return self.envs

    def get_opts(self):
        return self.opts

    def get_args(self):
        return self.args

    def get_name(self):
        return self.name

    def get_opt(self, name):
        return [self.opts[i + 1]
                for i in range(0, len(self.opts), 2) if self.opts[i] == name]

    def get_env(self, name):
        return self.envs.get(name)


def str_to_pairs(s):
    '''key=val key=val >> key, val, key, val'''

    pairs = []
    segs = shlex.split(s)

    for seg in segs:
        subsegs = seg.split("=", 1)
        if subsegs < 2:
            continue
        print "SS:", subsegs
        pairs.append(subsegs[0])
        pairs.append(subsegs[1])
        print "SS:", pairs
    return pairs


def dic_to_pairs(dic):
    return list(reduce(lambda x, y: x + y, dic.items()))


def lis_to_pairs(lis):
    '''Input anything, output a KV pairs list

    BASE:
        str: "aaa=bbb ccc=ddd"

        lis: ["aaa=bbb", "ccc=ddd", ["eee=fff"], {"aaa": "bbb", "ccc": "ddd"}]

        dic: {aaa:bbb, ccc:ddd}
    '''

    pairs = []
    cnt = len(lis)
    i = 0
    while i < cnt:
        obj = lis[i]
        i += 1

        if isinstance(obj, str):
            # Only support: aaa=AAA
            subsegs = obj.split("=", 1)
            print "OO:", subsegs
            if len(subsegs) > 1:
                # aaa=aaa
                pairs.extend(str_to_pairs(obj))
                continue

            # [ "aaa", "AAA" ] => aaa=AAA
            pairs.append(obj)
            pairs.append(str(lis[i]))
            i += 1
            continue

        if isinstance(obj, (list, tuple)):
            pairs.extend(lis_to_pairs(obj))
            continue

        if isinstance(obj, dict):
            pairs.extend(dic_to_pairs(obj))
            continue

    return pairs


def CallPkgInfo(dict):
    def __init__(self, dic):
        self.dic = dic

    def opt(self, opt):
        opts = dic.get("opts")
        if not opts:
            return []


def call_jsn_to_dic(data):
    '''data is a json string

    calldic

    json: {
        cmd: "cmd",
        envs: "aaa=bbb"
        envs: [aaa, bbb, ccc, ddd]
        envs: { aaa:bbb, ccc:ddd }

        opts: "aaa=bbb"
        opts: [aaa, bbb, ccc, ddd]
        opts: {aaa:bbb, ccc:ddd}
        opts: [{aaa:bbb}, "ccc=ddd"]

        args: ["aaa", "bbb", "ccc"]
    '''

    org = json.JSONDecoder().decode(data)
    calldic = CallDic()

    #
    # ENVS
    #
    envs = org.get("envs")
    pairs = lis_to_pairs([envs])
    calldic["envs"] = {k: v for k, v in zip(pairs[::2], pairs[1::2])}

    #
    # NAME
    #
    calldic["name"] = org.get("cmd") or org.get("command")

    #
    # OPTS
    #
    opts = org.get("opts")
    pairs = lis_to_pairs([opts])
    calldic["opts"] = pairs

    return calldic


def calldic_to_cmdline(calldic):

    cmdline = ""

    e = calldic.envs
    cmdline += " ".join(["%s='%s'" % (key, val) for key, val in e.items()])

    cmdline += calldic.name

    o = calldic.opts
    cmdline += " ".join(["--%s='%s'" % (o[i], o[i + 1])
                         for i in range(0, len(9), 2)])

    cmdline += " ".join(calldic.args)

    return cmdline


def call_cmd_to_dic(data):
    '''env=xxx command --opta=aaa arga argb'''
    if isinstance(data, str):
        segs = shlex.split(data)
    else:
        segs = data

    name, envs, opts, args = cmdline_split(segs)

    calldic = CallDic()
    calldic.name = name
    calldic.envs = envs
    calldic.opts = opts
    calldic.args = args

    return calldic


def cmdline_split(segs):
    '''Split command line segements to command, envs, opts, args

    cmdline = input()
    segs = shlex.split(cmdline)
    name, envs, opts, args = args_split(segs)

    aaa=AAA bbb=BBB ccc --ddd=DDD --eee EEE --ddd hehe -- --fff FFF ggg kkk
    > envs: { aaa:AAA, bbb:BBB }
    > name: ccc
    > opts: [ {ddd:DDD}, {eee:EEE}, {ddd:hehe}, ... ]
    > args: [ --fff, FFF, ggg, kkk ]
    '''

    envs = {}
    name = None
    opts = []
    args = []

    segc = len(segs)
    i = 0

    # envs stage
    while i < segc:
        seg = segs[i]
        print "SEGS[%d]: %s" % (i, seg)

        if seg.find("=") < 0:
            break

        env = seg.split("=", 1)
        envs[env[0]] = env[1]
        i += 1

    # name stage
    name = segs[i]
    i += 1

    # opts / segs
    while i < segc:
        seg = segs[i]
        print "SEGS[%d]: %s" % (i, seg)
        i += 1

        # Everything after -- are args
        if seg == "--":
            # Eat all and quit
            args.extend(segs[i:])
            break

        if seg.startswith("--"):
            # --opt aaa --opt bbb arga argb ...

            subsegs = seg.split("=", 1)
            if len(subsegs) > 1:
                # --lib=xxx.so

                opt, val = subsegs
            else:
                # --lib xxx.so

                if i >= segc:
                    break

                opt = seg
                val = segs[i]

            opts.append(opt[2:])
            opts.append(val)
            i += 1
        else:
            # cmd --aaa AAA xixi --bbb=BBB

            # xixi: args
            args.append(seg)

    return name, envs, opts, args


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


class DotDict(dict):

    def __init__(self, **kwargs):
        dict.update(self, kwargs)

    def __getattr__(self, k):
        return self.get(k, None)

    def __setattr__(self, k, v):
        self[k] = v


class KVPairs():
    '''Convert any format of key val pair to a list

    str: "aaa=bbb ccc=ddd"
    lis: ["aaa=bbb", "ccc=ddd", ["eee=fff"], {"aaa": "bbb", "ccc": "ddd"}]
    dic: {aaa:bbb, ccc:ddd}
    '''

    @staticmethod
    def fr_str(s):
        '''key=val key=val >> key, val, key, val'''

        pairs = []
        segs = shlex.split(s)

        for seg in segs:
            subsegs = seg.split("=", 1)
            if subsegs < 2:
                continue
            print "SS:", subsegs
            pairs.append(subsegs[0])
            pairs.append(subsegs[1])
            print "SS:", pairs
        return pairs

    @staticmethod
    def fr_dic(dic):
        if not dic:
            return []
        return list(reduce(lambda x, y: x + y, dic.items()))

    @staticmethod
    def fr_lis(lis):
        ''' lis: ["a=b", "c=d", ["eee=fff"], {"a": "b", "c": "d"}] '''

        pairs = []
        cnt = len(lis)
        i = 0
        while i < cnt:
            obj = lis[i]
            i += 1

            if obj is None:
                continue

            if isinstance(obj, (list, tuple)):
                pairs.extend(KVPairs.fr_lis(obj))
                continue

            if isinstance(obj, dict):
                pairs.extend(KVPairs.fr_dic(obj))
                continue

            if isinstance(obj, (str, unicode)):
                # Only support: aaa=AAA
                subsegs = obj.split("=", 1)
                if len(subsegs) > 1:
                    # aaa=aaa
                    pairs.extend(KVPairs.fr_str(obj))
                    continue

                # [ "aaa", "AAA" ] => aaa=AAA
                pairs.append(obj)
                pairs.append(str(lis[i]))
                i += 1
                continue

            print cp.r("!!!!!!! BAD TYPE !!!!!!!!")
            print "LIS:", lis
            print "OBJ:", cp.r(str(obj))
            print cp.r("!!!!!!! BAD TYPE !!!!!!!!")
            traceback.print_stack()

        return pairs

kvpair = KVPairs


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
