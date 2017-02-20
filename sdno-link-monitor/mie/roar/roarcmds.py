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
import subprocess
from kstat import kstat as kstat


class ExtCommands(object):
    def do_wblist(self, callman, wlist, blist):
        # if set wlist, use wlist else use blist
        cmds = {
            "dr": [self.docmd_dr, "KLog"],

            "stat": [self.docmd_stat, "Stat"],

            "q": [self.docmd_quit, "Exec"],

            "sh": [self.docmd_sh, "Shell"],

            "og": [self.docmd_og, "Conf"],
            "os": [self.docmd_os, "Conf"],
            "od": [self.docmd_od, "Conf"],
            "op": [self.docmd_op, "Conf"],
        }

        clist = set()

        # if defined white list, use white list
        wlist = wlist or []
        if wlist:
            clist = set(wlist)
        elif blist:
            clist = set(cmds.keys()) - set(blist)
        else:
            clist = set(cmds.keys())

        if not self.conf:
            clist -= set(["og", "os", "od", "op"])

        for k, v in cmds.items():
            if k in clist:
                c, g = v
                callman.addcmd(c, name=k, group=g)

    def __init__(self, callman, conf=None, wlist=None, blist=None):
        self.conf = conf
        self.do_wblist(callman, wlist, blist)

    def docmd_dr(self, cmdctx, calldic):
        '''Dynamic configure klog output

        Please direct input `dr' to see the help message.
        '''

        args = calldic.org_cmd[1:]

        os.environ["DR_RTCFG"] = os.environ.get("KLOG_RTCFG", "/tmp/klog.rtcfg")

        cmd = ['dr']
        cmd.extend(args)

        output = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
        return output

    def docmd_stat(self, cmdctx, calldic):
        '''Show kstat informations

        .opt -v Verbose
        Also show description.

        .opt -l as_list
        '''

        args = calldic.get_args()
        verb = calldic.get_opt("v")
        aslist = calldic.get_opt("l")

        '''Show runtime stastics'''
        res = kstat.dmp(args, verb, not aslist)
        return res

    def docmd_quit(self, cmdctx, calldic):
        '''Quit this application'''

        os._exit(0)

    def docmd_sh(self, cmdctx, calldic):
        '''Run shell command

        Call shell command in server. e.g:

        sh ls /

        Note: should not call the command block the console.
        '''
        args = calldic.org_cmd[1:]

        cmd = args
        output = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
        return output


    def docmd_og(self, cmdctx, calldic):
        '''Return the runtime configure by given query pattern

        og <type> <pattern>
            type:u  : used
            type:n  : not used
            type:t  : default value

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
        for arg in args:
            if not self.conf.rem(arg):
                nglist.append(arg)

        return {"nglist": nglist}

    def docmd_op(self, cmdctx, calldic):
        '''Save/Push the configure to file

        Usage: op [full]
        If full set, all the configure will be saved or else
        only modified saved
        '''

        args = calldic.get_args() or []

        try:
            full = args[0].lower() == "full"
        except:
            full = False
        return "OK" if self.conf.save(full) else "NG"
