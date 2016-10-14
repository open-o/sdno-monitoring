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
import subprocess
from kstat import kstat as kstat


def docmd_dr(cmdctx, calldic):
    '''
    Dynamic configure klog output
    '''
    args = calldic.get_args() or []

    os.environ["DR_RTCFG"] = os.environ.get(
        "KLOG_RTCFG", "/tmp/klog.rtcfg")
    os.system("dr %s" % " ".join(args))

    cmd = ['dr']
    cmd.extend(args)

    output = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
    return output


def docmd_stat(cmdctx, calldic):
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
