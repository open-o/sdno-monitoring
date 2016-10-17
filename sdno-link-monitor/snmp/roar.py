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


import sys
sys.path.append(".")

import time
import json
import socket
import shlex
import traceback
import pprint

import threading

import functools

from xlogger import klog
from utils import *

import gzip
import select
import eventfd

from StringIO import StringIO
import BaseHTTPServer
import shutil
from SocketServer import ThreadingMixIn
from roarcall import *
from deferdo import DeferDo
from bprint import *


klog.to_stdout()

### #####################################################################
# package.py
#
PLENC_RAW = 'R'
PLENC_ZIP = 'Z'

PLFMT_CMD = 'C'     # shell command line
PLFMT_XML = 'X'     # XML
PLFMT_JSN = 'J'     # JSON
PLFMT_BIN = 'B'     # Binary

CMDTYPE_CALL = 'C'
CMDTYPE_RESP = 'R'


def recv_and_disp(conn, callman):
    # conn: which socket or http connection
    # callman: with callman for these command
    tpkg = SockPkg.fr_skt(conn.sock)
    if not tpkg:
        klog.e("CLOSE: %d" % conn.sock.fileno())
        return False

    cpkg = CmdPkg.fr_dat(tpkg.hdr.pfmt, tpkg.payload)

    cmdctx = CmdCtx()
    cmdctx.conn = conn
    cmdctx.tpkg = tpkg
    cmdctx.cpkg = cpkg
    cmdctx.callman = callman

    if cpkg.hdr.cmdtype == CMDTYPE_CALL:
        DeferDo(call_defer, cmdctx)
    elif cpkg.hdr.cmdtype == CMDTYPE_RESP:
        DeferDo(resp_defer, cmdctx)
    else:
        klog.e("Close this socket")
        return False

    return True


### #####################################################################
# Transfer Pakage
#
class SockPkgHeader(object):

    def __init__(self, plen=0, penc=None, pfmt=None):
        self.plen = plen
        self.penc = penc
        self.pfmt = pfmt

    @staticmethod
    def dec(dat):
        if not dat:
            return None

        try:
            moye = dat[0:4]
            plen = int(dat[5:13], 16)
            penc = dat[14:15]
            pfmt = dat[16:17]
            grgn = dat[17:19]

            if moye != "MOYE" and grgn != "\r\n":
                klog.e("BAD TransHeader: '''%s'''" % dat)
                return None
        except:
            klog.e("BAD TransHeader: '''%s'''" % dat)
            return None

        return SockPkgHeader(plen, penc, pfmt)

    @staticmethod
    def enc(plen, penc, pfmt):
        return "MOYE %08X %s %s\r\n" % (plen, penc[0], pfmt[0])


class SockPkg(object):

    def __init__(self, hdr, payload):
        self.hdr = hdr
        self.payload = payload

    @staticmethod
    def to_bin(payload, penc, pfmt):
        '''Pack the payload and header into a RAW package'''
        if penc == PLENC_ZIP:
            payload = gzip.zlib.compress(payload)

        hdr = SockPkgHeader.enc(len(payload), penc, pfmt)
        res = hdr + payload
        return res

    @staticmethod
    def fr_skt(skt):
        '''Read a whole SockPkg'''

        def doenc(penc, data):
            return gzip.zlib.decompress(data) if penc == PLENC_ZIP else data

        hdr = SockPkgHeader.dec(sockget(skt, 19))
        if not hdr:
            return None

        dat = sockget(skt, hdr.plen)
        if not dat:
            return None

        # klog.d("pkg.hdr: %s" % str(hdr))
        # klog.d("pkg.dat: %s" % str(dat))

        return SockPkg(hdr, doenc(hdr, dat))


class SockConn(object):
    '''It's ONLY a socket'''

    def __init__(self, sock, host, port, block=False):
        '''sock or (host, port)'''
        self.host = host
        self.port = port
        self.sock = sock
        self.block = block

        self.iid = iidgen.iid()

        self.on_disconnect = []

        self.connect()

    def set_on_disconnect(self, cbk):
        self.on_disconnect.append(cbk)

    def call_on_disconnect(self):
        for cbk in self.on_disconnect:
            cbk(self)

    def connect(self):
        if not self.sock:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.sock.connect((self.host, int(self.port)))
            if not self.block:
                self.sock.setblocking(0)

    def disconnect(self):
        if self.sock:
            self.call_on_disconnect()

            self.sock.close()
            self.sock = None

    def recv(self, length=0):
        if not self.sock:
            return None

        left = length
        if not left:
            return self.sock.recv(left)

        dat = ""
        while left:
            tmp = self.sock.recv(left)
            if not tmp:
                return None
            left -= len(tmp)
            dat += tmp
        return dat

    def send(self, data):
        try:
            self.sock.sendall(data)
            return True
        except:
            klog.d("Send NG")
            return False


class Trans(object):

    def __init__(self):
        pass

    def bye(self):
        klog.d("Close and destroy this transition channel")

    def onclose(self):
        pass


class Trans_Socket(Trans):

    def __init__(self, sock, host, port, callman=None, mode='A'):
        '''Default is async mode'''

        self.mode = mode
        self.callman = callman

        blockmode = mode != 'A'
        self.conn = SockConn(sock, host, port, blockmode)

        if mode == 'A':
            # Async mode, should use epoll, and start a thread
            self.epollthread = EpollThread()
            self.epollthread.start()
            self.epollthread.epoll_set(
                self.conn.sock.fileno(), self.on_sockpkg)
        else:
            # Sync mode: send > recv, send > recv, ...
            pass

    def bye(self):
        self.conn.disconnect()
        del self.conn
        self.conn = None

        if self.mode == 'A':
            self.epollthread.close()

    def on_sockpkg(self, fileno, cookie):
        '''Data ready'''
        res = recv_and_disp(self.conn, self.callman)
        if not res:
            self.conn.disconnect()

    def pack(self, payload, plfmt):
        # Add MOYE Header
        return SockPkg.to_bin(payload, PLENC_RAW, plfmt)

    def send(self, callpkg, plfmt=PLFMT_JSN):
        sockpkg = self.pack(callpkg.payload, plfmt)
        return self.conn.send(sockpkg)

        '''
        if self.mode != 'A':
            # XXX: should wati till done
            res = recv_and_disp(self.conn, self.callman)
            if not res:
                self.conn.disconnect()
        '''


class EpollThread(threading.Thread):

    def __init__(self):
        threading.Thread.__init__(self)

        self.quit = False
        self.callbacks = {}

        self.epoll = select.epoll()

        self.efd = eventfd.EventFD()
        self.efd_fileno = self.efd.fileno()
        self.epoll_set(self.efd_fileno, cookie="eventfd")

    def wakeup(self):
        self.efd.set()

    def close(self):
        self.quit = True
        self.wakeup()

    def epoll_set(self, fileno, callback=None, cookie=None):
        dic = DotDict(fileno=fileno, callback=callback, cookie=cookie)
        self.callbacks[fileno] = dic
        self.epoll.register(fileno, select.EPOLLIN)

    def epoll_rem(self, fileno):
        dic = self.callbacks.get(fileno)
        if dic:
            self.epoll.unregister(fileno)
            del self.callbacks[fileno]

    def poll(self):
        events = self.epoll.poll()
        for fileno, event in events:
            dic = self.callbacks.get(fileno)
            if not dic or not dic.callback:
                klog.e("No callback found for %d" % fileno)
                continue

            try:
                dic.callback(dic.fileno, dic.cookie)
            except:
                traceback.print_exc()

    def run(self):
        while not self.quit:
            self.poll()


class CmdServer_Socket(EpollThread):
    '''CmdServer socket mode.
    '''

    def __init__(self, callman, port=8888):
        EpollThread.__init__(self)

        self.conns = {}

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        self.callman = callman

        self.port = port or 8888
        self.sock.bind(("0.0.0.0", self.port))
        self.sock.listen(20)
        self.sock.setblocking(0)

        self.epoll_set(self.sock.fileno(), self.new_connection, self)

        # Event callback for connection setup and break
        self.on_conn_new = []
        self.on_conn_del = []

        #
        # Protect this server
        #
        # 1. Black/White list to filter out some host
        # 2. Too frequency connection is prohibited
        #

        self.wblist = WBList()

    def conn_allowed(self, host, port):
        # 1.
        return True

    def set_on_conn_new(self, cbk):
        self.on_conn_new.append(cbk)

    def call_on_conn_new(self, sock):
        for cbk in self.on_conn_new:
            cbk(sock)

    def set_on_conn_del(self, cbk):
        self.on_conn_del.append(cbk)

    def call_on_conn_del(self, sock):
        for cbk in self.on_conn_del:
            cbk(sock)

    def new_connection(self, fileno, cookie):
        sock, [host, port] = self.sock.accept()

        if not self.conn_allowed(host, port):
            sock.close()
            return

        fileno = sock.fileno()
        klog.d("host:%s, port:%d, fileno:%d" % (host, port, fileno))

        conn = SockConn(sock, host, port)
        conn.set_on_disconnect(self.del_connection)

        self.conns[fileno] = conn
        sock.setblocking(0)
        self.epoll_set(fileno, self.ondata, self)

        self.call_on_conn_new(sock)

    def del_connection(self, conn):
        self.call_on_conn_del(conn.sock)

    def ondata(self, fileno, cookie):
        '''Recv a SockPkg'''

        conn = self.conns[fileno]
        res = recv_and_disp(conn, self.callman)
        if not res:
            conn.disconnect()
            del conn


# #######################################################################
## ######################################################################
### #####################################################################

### ###########################################################
# HTTPD
#


class ThreadedHTTPServer(ThreadingMixIn, BaseHTTPServer.HTTPServer):
    pass


class HTTPJsonCommandHandler(object, BaseHTTPServer.BaseHTTPRequestHandler):

    def __init__(self, request, client_address, server):
        self.protocol_version = "HTTP/1.1"
        BaseHTTPServer.BaseHTTPRequestHandler.__init__(
            self, request, client_address, server)
        self.json = {}

        self.request = request
        self.client_address = client_address
        self.server = server

    def encode_data(self, data):
        acceptEncodings = self.headers.get("Accept-Encoding", "").split(",")

        for acceptEncoding in acceptEncodings:
            if acceptEncoding == "gzip":
                out = StringIO()
                f = gzip.GzipFile(fileobj=out, mode='w', compresslevel=5)
                f.write(data)
                f.close()
                data = out.getvalue()
                return "gzip", data

            if acceptEncoding == "deflate":
                data = gzip.zlib.compress(data)
                return "deflate", data
        return None, data

    def resp_data(self, status, data=None, path=None, contenttype=None):
        length = 0
        fp = None

        if data:
            encoding, data = self.encode_data(data)

            if encoding:
                self.send_header("Content-Encoding", encoding)

            fp = StringIO()
            fp.write(data)
        elif path:
            fp = open(path, "r")
            fp.seek(0, 2)
        else:
            fp = None

        if fp:
            length = fp.tell()
            fp.seek(0, 0)

        contenttype = contenttype or "application/json"

        self.send_response(status)
        self.send_header("Content-type", contenttype)
        self.send_header("Content-Length", str(length))
        self.end_headers()

        if fp:
            self._copyfile(fp, self.wfile)

    def setack(self, iid, content):
        dic = {}

        if isinstance(content, tuple):
            msg, errcode = content[:2]
        else:
            msg = content
            errcode = 0

        dic["iid"] = iid
        dic["errcode"] = errcode
        dic["ts"] = time.asctime()

        if errcode:
            dic["errmsg"] = str(msg)
        else:
            dic["errmsg"] = ""
            dic["content"] = msg

        dic["command"] = self.command
        self.ack.append(dic)

    def jget(self, name, defval=None):
        res = self.json.get(name, defval)
        return res

    def disp_command(self):
        self.iid = self.jget("iid")
        self.command = self.jget("command", "")
        self.envs = self.jget("envs", {})
        self.opts = self.jget("opts", [])
        self.args = self.jget("args", [])

        self.ack = []

        try:
            docmd_func = getattr(self, 'docmd_' + self.command)
            code = docmd_func()
        except:
            # traceback.print_exc()
            try:
                docmd_func = getattr(self, 'docmd__failthrough')
                code = docmd_func()
            except:
                traceback.print_exc()
                code = 404

        return code

    def do_POST(self):
        varprt(self, "do_POST")
        host = self.client_address[0]
        try:
            content_length = int(self.headers.get("Content-Length", "0"))
            payload = self.rfile.read(content_length) or "{}"
            self.json = json.JSONDecoder().decode(payload)

            printb(self.json, "do_POST.Request")

            code = self.disp_command()

            printb(self.ack, "do_POST.Response")

            printb(self.ack, "HTTPD.ack")
            self.resp_data(code, data=json.dumps(self.ack))
        except:
            traceback.print_exc()
            self.resp_data(404)
            return

    def _copyfile(self, source, outputfile):
        shutil.copyfileobj(source, outputfile)


class CmdServer_Http(threading.Thread):

    def __init__(self, port, cmdHandler):
        threading.Thread.__init__(self)
        self.port = port

        server_class = ThreadedHTTPServer
        handler_class = cmdHandler
        server_address = ('', port)

        self.httpd = server_class(server_address, handler_class)
        self.start()

    def run(self):
        self.httpd.serve_forever()


class Trans_Http(Trans):

    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.httpclient = httplib.HTTPConnection('localhost', port, timeout=10)

    def pkg_disp(self, callman):
        # conn: which socket or http connection
        # callman: with callman for these command
        cmdctx = CmdCtx()
        cmdctx.cpkg = cpkg
        cmdctx.callman = callman

        if cpkg.hdr.cmdtype == CMDTYPE_CALL:
            DeferDo(call_defer, cmdctx)
        elif cpkg.hdr.cmdtype == CMDTYPE_RESP:
            DeferDo(resp_defer, cmdctx)
        else:
            klog.e("Close this socket")

    def send(self, callpkg, plfmt=PLFMT_JSN):
        params = json.dumps(callpkg.payload)

        headers = {
            'Content-type': 'application/x-www-form-urlencoded',
            'Accept': 'text/plain'
        }

        try:
            self.httpclient.request('POST', '', params, headers)
            r = self.httpclient.getresponse()

            self.pkg_disp(self.callman)

            if r.status == 200:
                dat = r.read()
                obj = json.JSONDecoder().decode(str(dat))
                dat = r.getheaders()
        except:
            traceback.print_exc()
            pass


# #######################################################################
## ######################################################################
### #####################################################################
#### ####################################################################
##### ###################################################################
###### ##################################################################


### #####################################################################
# Command Package: Base Class
#
class CmdPkg(object):
    '''CmdPkg is: Call or Resp, it can be carried by socket or http.

    The data can be json or xml
    '''

    # {fmt: {to_dic, to_dat }}
    _cmdpkg_backends = {}

    @staticmethod
    def set_backend(fmt, to_dic=None, to_dat=None):
        CmdPkg._cmdpkg_backends[fmt] = dict(to_dic=to_dic, to_dat=to_dat)

    @staticmethod
    def get_backend(fmt):
        dic = CmdPkg._cmdpkg_backends.get(fmt)
        if not dic:
            return None, None
        return dic.get("to_dic"), dic.get("to_dat")

    def __init__(self):
        #
        # Common part
        #

        # Madatory:SockPkg: Header
        self.hdr = DotDict(pfmt=None, csn=None, iid=None, cmdtype=None)

        #
        # Call part
        #
        # self.call = None

        #
        # Resp part
        #
        # self.resp = None

    @staticmethod
    def to_dat(pfmt, data):
        '''Encode dic to data'''

        to_dic_func, to_dat_func = CmdPkg.get_backend(pfmt)
        if not to_dat_func:
            return None

        return to_dat_func(data)

    @staticmethod
    def fr_dat(pfmt, data):
        '''Decode data into dic'''

        to_dic_func, to_dat_func = CmdPkg.get_backend(pfmt)
        if not to_dic_func:
            return None

        dic = to_dic_func(data)
        cmdpkg = CmdPkg()

        # Madatory: Header
        cmdpkg.hdr.pfmt = pfmt
        cmdpkg.hdr.csn = dic["csn"]
        cmdpkg.hdr.cmdtype = dic["cmdtype"]
        cmdpkg.hdr.iid = dic["iid"]

        # Payload
        if cmdpkg.hdr.cmdtype == CMDTYPE_CALL:
            cmdpkg.call = CallDic.fr_jsn(dic)
            return cmdpkg

        if cmdpkg.hdr.cmdtype == CMDTYPE_RESP:
            cmdpkg.resp = RespDic.fr_jsn(dic)
            return cmdpkg

        return None


### #####################################################################
# Command Package: Sub classes
#
def cmdpkg_json_to_dic(data):
    return json.JSONDecoder().decode(data)


def cmdpkg_json_to_dat(dic):
    if "csn" not in dic:
        dic["csn"] = csngen.csn()

    if "cmdtype" not in dic:
        dic["cmdtype"] = CMDTYPE_CALL

    dic["iid"] = iidgen.iid()

    try:
        return json.dumps(dic)
    except:
        try:
            return varfmt(dic)
        except:
            dic.resp = str(dic.resp)
            return json.dumps(dic)

CmdPkg.set_backend(PLFMT_JSN, cmdpkg_json_to_dic, cmdpkg_json_to_dat)


### ###########################################################
# Play with json command package
#
class RespDic(DotDict):
    '''Data part of a response

    Fields:
        errcode
        errmsg
        notice
        content

    Input:
        *ONLY* json format

    Output:
        None
    '''

    #
    # Variable Access
    #
    def get_errcod(self, env):
        return self.errcode

    def get_errmsg(self):
        return self.errmsg

    def get_notice(self):
        return self.notice

    def get_content(self):
        return self.content

    #
    # Interface
    #
    @staticmethod
    def fr_jsn(data):
        if isinstance(data, str):
            org = json.JSONDecoder().decode(data)
        else:
            org = data

        respdic = RespDic()

        respdic.errcode = org.get("errcode")
        respdic.errmsg = org.get("errmsg")
        respdic.notice = org.get("notice")
        respdic.content = org.get("content") or org.get("resp")

        return respdic


# Inner format of call data
class CallDic(DotDict):
    '''Data part of a call.

    Fields:
        name, envs, opts, args

    Input:
        jsn, cmd, xml etc

    Output:
        jsn, cmd, xml etc

    Action:
        get fields, such as name envs opts, args
    '''

    #
    # Access to fields
    #
    def get_envs(self, env):
        return self.envs

    def get_opts(self):
        return self.opts

    def get_args(self):
        return self.args

    def get_name(self):
        return self.name

    def get_opt(self, name):
        o = self.opts
        return [o[i + 1] for i in range(0, len(o), 2) if o[i] == name]

    def get_env(self, name):
        return self.envs.get(name)

    #
    # Operations/Interfaces
    #
    @staticmethod
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
            # print "SEGS[%d]: %s" % (i, seg)

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
            # print "SEGS[%d]: %s" % (i, seg)
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
                    # print "opt:", opt
                    # print "val:", val
                else:
                    # --lib xxx.so

                    if i >= segc:
                        break

                    opt = seg
                    val = segs[i]

                    # print "1opt:", opt
                    # print "1val:", val
                    i += 1

                opts.append(opt[2:])
                opts.append(val)
            else:
                # cmd --aaa AAA xixi --bbb=BBB

                # xixi: args
                args.append(seg)

        return name, envs, opts, args

    @staticmethod
    def fr_jsn(data):
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

            # untouched fields
            iid: "xxxxxxxxxxxx"
            csn: "xxxxxxxxxxxx"
        '''

        data = data or {}
        if isinstance(data, str):
            org = json.JSONDecoder().decode(data)
        else:
            org = data

        org = org or {}
        calldic = CallDic()
        for key, val in org.items():
            if key in ["envs", "cmd", "command", "opts", "args"]:
                # These fields is command fields
                continue
            calldic[key] = val

        #
        # ENVS
        #
        envs = org.get("envs")
        pairs = kvpair.fr_lis([envs])
        calldic.envs = {k: v for k, v in zip(pairs[::2], pairs[1::2])}

        #
        # NAME
        #
        calldic.name = org.get("cmd") or org.get("command") or org.get("name")

        #
        # OPTS
        #
        opts = org.get("opts")
        pairs = kvpair.fr_lis([opts])
        calldic.opts = pairs

        #
        # ARGS
        #
        calldic.args = org.get("args")

        calldic.org_jsn = data
        return calldic

    @staticmethod
    def fr_cmd(data):
        '''env=xxx command --opta=aaa arga argb'''
        if isinstance(data, str):
            segs = shlex.split(data)
        else:
            segs = data

        name, envs, opts, args = CallDic.cmdline_split(segs)

        calldic = CallDic()
        calldic.name = name
        calldic.envs = envs
        calldic.opts = opts
        calldic.args = args

        calldic.org_cmd = data
        return calldic

    def to_cmd(self, dic):
        cmd = ""

        e = self.envs
        cmd += " ".join(["%s='%s'" % (key, val) for key, val in e.items()])

        cmd += " " + self.name + " "

        o = self.opts
        cmd += " ".join(["--%s='%s'" % (o[i], o[i + 1])
                         for i in range(0, len(o), 2)])

        cmd += "-- " + " ".join(self.args)

        return cmd

    @staticmethod
    def fr_xml(data):
        pass

    def to_xml(self, dic):
        pass


### ###########################################################
# Event for a sent call
#
class CallEvt(DotDict):
    '''Save all the event callback for a Call.

    Have no idea of the call, cmdPkg should link them

    > send - [sent] - fail/kill

    > send - sent - [on|ng]

    > LAST: fail, kill, done, cs
    '''

    EVSEND = 'send'     # Emit before send

    def onsend(self, func=None, cookie=None):
        '''onfunc("send", cookie, callpkg)'''
        return self.on(CallEvt.EVSEND, func, cookie)

    EVSENT = 'sent'     # Emit after send

    def onsent(self, func=None, cookie=None):
        '''onfunc("sent", cookie, callpkg)'''
        return self.on(CallEvt.EVSENT, func, cookie)

    EVFAIL = 'fail'     # Emit error

    def onfail(self, func=None, cookie=None):
        '''onfunc("fail", cookie, callpkg)'''
        return self.on(CallEvt.EVFAIL, func, cookie)

    EVDONE = 'done'     # Last emit

    def ondone(self, func=None, cookie=None):
        '''onfunc("done", cookie, callpkg, respdic)'''
        return self.on(CallEvt.EVDONE, func, cookie)

    EVKILL = 'kill'     # Call is cancelled

    def onkill(self, func=None, cookie=None):
        '''onfunc("kill", cookie, callpkg)'''
        return self.on(CallEvt.EVKILL, func, cookie)

    EVOK = 'ok'         # Resp got

    def onok(self, func=None, cookie=None):
        '''onfunc("ok", cookie, cmdctx, respdic)'''
        return self.on(CallEvt.EVOK, func, cookie)

    EVNG = 'ng'         # Resp got, but errcode set

    def onng(self, func=None, cookie=None):
        '''onfunc("ng", cookie, cmdctx, respdic)'''
        return self.on(CallEvt.EVNG, func, cookie)

    EVCS = 'cs'         # Timeout

    def oncs(self, func=None, cookie=None):
        '''onfunc("cs", cookie, callpkg)'''
        return self.on(CallEvt.EVCS, func, cookie)

    def on(self, ev, func=None, cookie=None):
        # klog.d("SET CallEvt.on: e:%s, f:%s, c:%s" % (ev, func.func_name, str(cookie)))
        callenv = DotDict(func=func, cookie=cookie)
        self[ev] = self.get(ev, []) + [callenv]
        return self

    def call(self, name, on, *args, **kwargs):
        '''onXxx(cookie, callpkg, respdic)'''
        callenvs = self.get(on)
        if not callenvs:
            # klog.e("EE: %s: No callenv for '%s'" % (name, on))
            pass
        else:
            for callenv in callenvs:
                if not callenv.func:
                    klog.e("callenv.func is none: %s" % str(callenv))
                    continue
                callenv.func(on, callenv.cookie, *args, **kwargs)


### ###########################################################
# CallPkg
#

class CallQueue(object):
    _calls = {}

    @staticmethod
    def set(key, call):
        CallQueue._calls[key] = call

    @staticmethod
    def get(key):
        return CallQueue._calls.get(key)

    @staticmethod
    def rem(key):
        try:
            del CallQueue._calls[key]
        except:
            pass

    @staticmethod
    def foreach(func, cookie=None):
        for key, call in CallQueue._calls.items():
            func(key, call, cookie)

    def __dict__(self):
        klog.e("%s" % str(self._calls))
        return self._calls

callqueue = CallQueue()


# CallPkg = CallEvt + CallDic
class CallPkg():

    def __init__(self, calldic, callevt):
        self.calldic = calldic
        self.callevt = callevt

        cpkg = cmdpkg_json_to_dat(self.calldic)
        self.payload = cpkg

        self.trans = None

    @staticmethod
    def new(cmd, cookie=None, **kwargs):
        calldic = CallDic.fr_cmd(cmd)
        callevt = CallEvt()

        for evt, cbk in kwargs.items():
            callevt.on(evt, cbk, cookie)

        return CallPkg(calldic, callevt)

    def __del__(self):
        conn = self.trans.conn
        key = "%s:%s:%s" % (conn.host, conn.port, self.calldic.csn)
        callqueue.rem(key)

    def queue(self):
        conn = self.trans.conn
        key = "%s:%s:%s" % (conn.host, conn.port, self.calldic.csn)
        callqueue.set(key, self)

    def postvia(self, trans):
        '''Post (Send without wait) to cmdConn'''
        self.trans = trans
        self.queue()

        callname = self.calldic.name
        self.callevt.call(callname, "send", self)
        res = trans.send(self, PLFMT_JSN)
        if res:
            self.callevt.call(callname, "sent", self)
        else:
            self.callevt.call(callname, "fail", self)

    def sendvia(self, trans):
        '''Send and wait'''

        event = threading.Event()

        def wakeup(ev, cookie, *args):
            klog.d("sendvia.wakeup.ev: %s" % ev)
            event.set()

        self.callevt.oncs(wakeup).ondone(wakeup).onfail(wakeup)
        self.postvia(trans)
        event.wait()


class CmdGC(threading.Thread):
    '''All the Cmd is link to this'''

    def __init__(self):
        threading.Thread.__init__(self)
        self.quit = False
        self.start()

    def dogc(self, key, call, cookie):
        klog.e(key)
        pass

    def run(self):
        while not self.quit:
            now = time.time()
            # callqueue.foreach(self.dogc, None)
            # klog.e("callqueue:%d" % len(callqueue._calls))
            time.sleep(5)

cmdgc = CmdGC()


def cmd_forward(cmdname, cmdctx, calldic):
    return cmdctx.callman.call(cmdctx, cmdname)


def cmd_help(cmdname, cmdctx):
    handler = cmdctx.callman.name_handler_map.get(cmdname)
    if handler:
        return False, None
    return True, handler.mkdoc(cmdname)


class CmdCtx(DotDict):
    '''Information of collection of call

    self.conn   : Socket or Http connection
    self.tpkg   : MOYE package or HTTP package
    '''

    def __init__(self, **kwargs):

        # CmdConn(
        #   .fileno, .socket, .host, .port
        #   )
        # CmdConn(
        #   .url
        #   )
        self.conn = None

        # SockPkg(
        #   .hdr.plen, .hdr.penc, .hdr.pfmt, .payload
        #   )
        # HttpPkg(
        #   ???????????? TODO FIXME
        #   )
        self.tpkg = None

        # CmdPkg(
        #   .hdr.pfmt, .hdr.csn, .hdr.iid, .hdr.cmdtype,
        #   .call.envs, .call.name, .call.opts, .call.args
        #   )
        self.cpkg = None

        DotDict.__init__(self, **kwargs)


def call_defer(cmdctx):

    varprt(cmdctx.cpkg, "call_defer.cmdctx.cpkg")

    callman = cmdctx.callman

    try:
        res = callman.fullcall(cmdctx)
    except:
        errmsg = "NG: Bad command '%s'" % cmdctx.cpkg.call.name
        errmsg = traceback.format_exc()
        res = dict(errmsg=errmsg, errcode=1)
        klog.e(traceback.format_exc())

    # res = dict(content=str, errcode=int, close=int, notice=str)
    if res is not None:

        if "close" in res:
            close = res.get("close", 0)
            del res["close"]

        #
        # Send back the response
        #
        res["csn"] = cmdctx.cpkg.hdr.csn
        res["cmdtype"] = CMDTYPE_RESP
        res["name"] = cmdctx.cpkg.call.name

        ### varprt(res, "Call response ....")
        payload = CmdPkg.to_dat(cmdctx.cpkg.hdr.pfmt, res)

        pkg = SockPkg.to_bin(payload, PLENC_RAW, cmdctx.cpkg.hdr.pfmt)

        cmdctx.conn.send(pkg)


def resp_defer(cmdctx):
    # From csn found original command and evt, then call the event

    # varprt(cmdctx, "resp_defer.cmdctx")

    conn = cmdctx.conn
    cpkg = cmdctx.cpkg

    key = "%s:%s:%s" % (conn.host, conn.port, cpkg.hdr.csn)
    callpkg = callqueue.get(key)

    respdic = cmdctx.cpkg.resp
    callevt = callpkg.callevt

    cmdctx.callpkg = callpkg

    #
    # ok, ng,
    #
    if respdic.errcode:
        callevt.call(callpkg.calldic.name, "ng", cmdctx, respdic)
    else:
        callevt.call(callpkg.calldic.name, "ok", cmdctx, respdic)

    callevt.call(callpkg.calldic.name, "done", cmdctx, respdic)

    callqueue.rem(key)


class CallHandler(DotDict):
    '''docall_xxx

    env=xxx env=xxx cmd --opta xxx --opt2=ddd -- --arga argb ..
    env=xxx env=xxx cmd --opta xxx --opt2=ddd --opt optval args ...
    '''

    def mkdoc(self, name, fmt=None):
        '''
        {
            name: xxx
            group: xxxx
            sdsc: xxx
            ldsc: xxx
            opts: {
                name: xxx
                defv: xxx
                sdsc: xxx
                ldsc: xxx
            }
        }
        '''
        fmt = fmt or 'xml'
        dic = DotDict()

        dic.name = name
        dic.group = self.group

        dic.sdsc = self.sdsc
        dic.ldsc = self.ldsc

        dic.opts = []

        opts = self.opts or {}
        for opt, inf in opts.items():
            defval, sdsc, ldsc = inf
            dic.opts.append({"name": opt,
                             "sdsc": sdsc,
                             "ldsc": ldsc,
                             "defv": defv
                             })

        return dic

    def mkcmd(self, args):
        opts = []
        missopt = []

        for o, v in self.opts.items():
            opt = "--" + o
            if opt not in args:
                missopt.append(o)
                continue

            index = args.index(opt)
            try:
                opts.append(args[index + 1])
                opts.insert(-1, opt)
                args[index] = None
                args[index + 1] = None
            except:
                pass

        for o in missopt:
            opts.append("--" + o)
            opts.append(self.opts[o][0])

        args = filter(lambda x: x is not None, args)

        return args[0], opts, args[1:]

    def run(self, cmdctx):
        return self.func(cmdctx, cmdctx.cpkg.call)

    def __init__(self, funcname):
        self.funcname = funcname
        self.group = "Ungrouped"

        self.func = None
        self.opts = {}

    def setgroup(self, group):
        self.group = group or "Ungrouped"

    def setfn(self, func):
        self.func = func

    def setcmd(self, sdsc, ldsc):
        self.sdsc = sdsc
        self.ldsc = ldsc

    def setopt(self, opt, defval, sdsc, ldsc):
        self.opts[opt] = [defval, sdsc, ldsc]


class CallManager(object):
    #
    # Load all the docall_xxx
    #

    def scancmds(self, inst=None, prefix=None, group=None):
        '''Add functions in a instance to CallManager'''

        inst = inst or self
        prefix = prefix or "docall_"
        offset = len(prefix)

        for var in dir(inst.__class__):
            if var.startswith(prefix):
                fn = getattr(inst, var)
                self.addcmd(fn, var[offset:], group=group)

    def __init__(self):
        self.call_handlers = []
        self.name_handler_map = {}
        self.name_list = []

        #
        # Hook functions
        self.precmds = set()
        self.postcmds = set()

        # Get the real globals
        depth = 1
        while True:
            try:
                sys._getframe(depth)
                depth += 1
            except:
                break

        self._globals = sys._getframe(depth - 1).f_globals

        # Load the builtin commands
        BuiltinCommands(self)

    #
    # Add command
    #
    def find_handler(self, name, nametype='fc'):
        '''Find handler according to name

        name can be command name or function name
        '''

        if "f" in nametype:
            # Treat name as function name
            for cmdname, handler in self.name_handler_map.items():
                if handler.funcname == name:
                    return handler

        if "c" in nametype:
            # Treat name as command name
            handler = self.name_handler_map.get(name, None)
            return handler

        return None

    def addopt(self, fn, opt, val, sdsc=None, ldsc=None):
        funcname = fn.__name__
        callhandler = self.find_handler(funcname) or CallHandler(funcname)
        self.call_handlers.append(callhandler)

        callhandler.setopt(opt, val, sdsc, ldsc)

    #
    # Decorator
    #
    def decopt(self, opt, val, sdsc=None, ldsc=None):
        def decorator(fn):
            self.addopt(fn, opt, val, sdsc, ldsc)
            return fn
        return decorator

    def addcmd(self, fn, name=None, group=None, sdsc=None, ldsc=None):
        if fn.__doc__:
            lines = fn.__doc__.split("\n")
            doc_sdsc = lines[0].strip()
            doc_ldsc = "\n".join([l.strip() for l in lines[2:]])
        else:
            doc_sdsc = None
            doc_ldsc = None

        funcname = fn.__name__

        if self.find_handler(funcname):
            print "WARNING! cmd(%s <> %s) exists, will overwrite it" % (funcname, str(name))

        callhandler = self.find_handler(funcname) or CallHandler(funcname)
        self.call_handlers.append(callhandler)

        callhandler.setcmd(doc_sdsc, doc_ldsc)
        callhandler.setgroup(group)
        callhandler.setfn(fn)

        self.name_handler_map[name or funcname] = callhandler
        self.name_list = sorted([a for a, _ in self.name_handler_map.items()])

    #
    # Decorator
    #
    def deccmd(self, name=None, group=None, sdsc=None, ldsc=None):
        def decorator(fn):
            self.addcmd(fn, name, group, sdsc, ldsc)

            @functools.wraps(fn)
            def wrapper(*args, **kwargs):
                res = fn(*args, **kwargs)
                return res
            return wrapper
        return decorator

    #
    # Command hook
    #
    def precmd_set(self, fn):
        self.precmds.add(fn)

    def precmd_del(self, fn):
        if fn in self.precmds:
            del self.precmds[fn]

    def precmd(self, cmdctx):
        '''
        for fn in self.precmds:
            fn(cmdctx, call)
        '''
        pass

    def postcmd_set(self, fn):
        self.postcmds.add(fn)

    def postcmd_del(self, fn):
        if fn in self.postcmds:
            del self.postcmds[fn]

    def postcmd(self, cmdctx, res):
        for fn in self.postcmds or []:
            fn(cmdctx, res)

    #
    # Call command
    #
    def call(self, cmdctx, name=None):
        notice = None

        name = name or cmdctx.cpkg.call.name

        callhandler = self.name_handler_map.get(name)
        if not callhandler:
            klog.e("Call '%s' not found" % name)
            raise KeyError

        res = callhandler.run(cmdctx)
        if res is None:
            return

        # XXX:
        #
        # res:
        # string:
        # tuple: "Content or Error Message" errorCode closeIndicator
        # dict: content=XXX errcode=XXX close=XXX
        #
        errcode, close = 0, 0
        dic = dict()
        try:
            if isinstance(res, tuple):
                content = res[0]
                errcode = int(res[1])
                close = int(res[2])
            else:
                content = res
                errcode = 0
                close = 0
        except:
            pass

        dic["close"] = close
        if errcode:
            dic["errcode"] = errcode
            if content:
                dic["errmsg"] = content
        else:
            dic["resp"] = content

        if notice:
            dic["notice"] = notice

        return dic

    def fullcall(self, cmdctx):
        self.precmd(cmdctx)
        res = self.call(cmdctx)
        self.postcmd(cmdctx, res)
        return res


class IngCallsManager():
    calls = []

    @staticmethod
    def add(call):
        IngCallsManager.call.append(call)


class IngCmdServerManager():
    servers = []


class BuiltinCommands(object):

    def __init__(self, callman):
        self.callman = callman
        callman.scancmds(inst=self, prefix="docmd_", group="builtin")

    def docmd_list(self, cmdctx, calldic):
        '''List all the supported commands'''
        return self.callman.name_list

    def docmd_man(self, cmdctx, calldic):
        '''Show help for commands'''

        args = calldic.get_args() or []

        if len(args) < 1:

            '''
            [
                {
                    group: Name
                    commands: [
                        aaa,
                        bbb
                    ]
                }
            ]
            '''

            grps = {}
            for name, handler in self.callman.name_handler_map.items():
                g = handler.group
                cmds = grps.get(g) or []
                cmds.append(name)
                grps[g] = cmds

            printb(grps, "#############")
            return grps

        cmdname = args[0]
        handler = self.callman.name_handler_map.get(cmdname)
        if not handler:
            return "Command not found: %s" % cmdname

        try:
            return handler.mkdoc(cmdname)
        except:
            traceback.print_exc()
            return "Bad command :%s" % fn

    def docmd_vars(self, cmdctx, calldic):
        '''Dump vars'''
        curMod = self.callman._globals

        args = calldic.get_args() or []
        if len(args) > 0:
            try:
                # a.b.c
                mods = args[0].split(".")
                for mod in mods:
                    if isinstance(curMod, dict):
                        curMod = curMod[mod]
                    else:
                        curMod = vars(curMod)[mod]

                if hasattr(curMod, "__dict__"):
                    reply = pprint.pformat(vars(curMod))
                else:
                    reply = pprint.pformat(curMod)
            except:
                reply = "ERROR: '%s' NOT FOUND OR NOT DICT" % args[0]
        else:
            reply = {}
            for k, v in curMod.items():
                try:
                    reply[k] = pprint.pformat(v)
                except:
                    try:
                        reply[k] = str(v)
                    except:
                        pass

        return reply
