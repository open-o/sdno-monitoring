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

import traceback
import subprocess

from dotdict import DotDict
from xlogger import klog

oid = DotDict({
    "ipAdEntAddr":                  ".1.3.6.1.2.1.4.20.1.1",
    "ipAdEntIfIndex":               ".1.3.6.1.2.1.4.20.1.2",
    "ipAdEntNetMask":               ".1.3.6.1.2.1.4.20.1.3",
    "ipAdEntBcastAddr":             ".1.3.6.1.2.1.4.20.1.4",
    "ipAdEntReasmMaxSize":          ".1.3.6.1.2.1.4.20.1.5",

    "ifIndex":                      ".1.3.6.1.2.1.2.2.1.1",
    "ifDescr":                      ".1.3.6.1.2.1.2.2.1.2",
    "ifType":                       ".1.3.6.1.2.1.2.2.1.3",
    "ifMtu":                        ".1.3.6.1.2.1.2.2.1.4",
    "ifSpeed":                      ".1.3.6.1.2.1.2.2.1.5",
    "ifPhysAddress":                ".1.3.6.1.2.1.2.2.1.6",
    "ifAdminStatus":                ".1.3.6.1.2.1.2.2.1.7",
    "ifOperStatus":                 ".1.3.6.1.2.1.2.2.1.8",
    "ifLastChange":                 ".1.3.6.1.2.1.2.2.1.9",
    "ifInOctets":                   ".1.3.6.1.2.1.2.2.1.10",
    "ifInUcastPkts":                ".1.3.6.1.2.1.2.2.1.11",
    "ifInNUcastPkts":               ".1.3.6.1.2.1.2.2.1.12",
    "ifInDiscards":                 ".1.3.6.1.2.1.2.2.1.13",
    "ifInErrors":                   ".1.3.6.1.2.1.2.2.1.14",
    "ifInUnknownProtos":            ".1.3.6.1.2.1.2.2.1.15",
    "ifOutOctets":                  ".1.3.6.1.2.1.2.2.1.16",
    "ifOutUcastPkts":               ".1.3.6.1.2.1.2.2.1.17",
    "ifOutNUcastPkts":              ".1.3.6.1.2.1.2.2.1.18",
    "ifOutDiscards":                ".1.3.6.1.2.1.2.2.1.19",
    "ifOutErrors":                  ".1.3.6.1.2.1.2.2.1.20",
    "ifOutQLen":                    ".1.3.6.1.2.1.2.2.1.21",
    "ifSpecific":                   ".1.3.6.1.2.1.2.2.1.22",

    "ifName":                       ".1.3.6.1.2.1.31.1.1.1.1",
    "ifInMulticastPkts":            ".1.3.6.1.2.1.31.1.1.1.2",
    "ifInBroadcastPkts":            ".1.3.6.1.2.1.31.1.1.1.3",
    "ifOutMulticastPkts":           ".1.3.6.1.2.1.31.1.1.1.4",
    "ifOutBroadcastPkts":           ".1.3.6.1.2.1.31.1.1.1.5",
    "ifHCInOctets":                 ".1.3.6.1.2.1.31.1.1.1.6",
    "ifHCInUcastPkts":              ".1.3.6.1.2.1.31.1.1.1.7",
    "ifHCInMulticastPkts":          ".1.3.6.1.2.1.31.1.1.1.8",
    "ifHCInBroadcastPkts":          ".1.3.6.1.2.1.31.1.1.1.9",
    "ifHCOutOctets":                ".1.3.6.1.2.1.31.1.1.1.10",

    "ifHCOutUcastPkts":             ".1.3.6.1.2.1.31.1.1.1.11",
    "ifHCOutMulticastPkts":         ".1.3.6.1.2.1.31.1.1.1.12",
    "ifHCOutBroadcastPkts":         ".1.3.6.1.2.1.31.1.1.1.13",
    "ifLinkUpDownTrapEnable":       ".1.3.6.1.2.1.31.1.1.1.14",
    "ifHighSpeed":                  ".1.3.6.1.2.1.31.1.1.1.15",
    "ifPromiscuousMode":            ".1.3.6.1.2.1.31.1.1.1.16",
    "ifConnectorPresent":           ".1.3.6.1.2.1.31.1.1.1.17",
    "ifAlias":                      ".1.3.6.1.2.1.31.1.1.1.18",
    "ifCounterDiscontinuityTime":   ".1.3.6.1.2.1.31.1.1.1.19",

    # HUAWEI-MPLS-EXTEND-MIB
    "hwMplsTunnelStatisticsTunnelIndex":    ".1.3.6.1.4.1.2011.5.25.121.1.14.1.1",
    "hwMplsTunnelStatisticsIngressLSRId":   ".1.3.6.1.4.1.2011.5.25.121.1.14.1.2",
    "hwMplsTunnelStatisticsEgressLSRId":    ".1.3.6.1.4.1.2011.5.25.121.1.14.1.3",
    "hwMplsTunnelStatisticsHCInOctets":     ".1.3.6.1.4.1.2011.5.25.121.1.14.1.4",
    "hwMplsTunnelStatisticsHCOutOctets":    ".1.3.6.1.4.1.2011.5.25.121.1.14.1.5",
})

class SnmpOper():
    @classmethod
    def splitline(cls, line, oid):
        def convert(type, value):
            table = {
                    "Counter32": int,
                    "Counter64": int,
                    "Gauge32": int,
                    "Hex-STRING": str.strip,
                    "INTEGER": int,
                    "IpAddress": str,
                    "OID": str,
                    "STRING": lambda x: x[1:-1],
                    "Timeticks": str,
                    }
            return table.get(type, str)(value)

        try:
            pfxlen = len(oid) + 1
            segs = line.split()
            if segs > 3 and segs[0].startswith(oid):
                name = segs[0][pfxlen:]
                type = segs[2][:-1]
                value = convert(type, line.split(":")[1][1:])
                return name, type, value
        except:
            pass
        return None, None, "What????"

    @classmethod
    def subcall(cls, cmd):
        try:
            return subprocess.check_output(cmd).replace("\r", "\n").split("\n")
        except:
            klog.e("CMD:%s\r\nBT:%s" % (cmd, traceback.format_exc()))
            return []

    @classmethod
    def get(cls, host, comm, vern, oid):
        cmd = ['snmpget', '-Oe', '-On', '-v', vern, '-c', comm, host, oid]
        lines = cls.subcall(cmd)
        return cls.splitline(lines[0], oid)

    @classmethod
    def walk(cls, host, comm, vern, oid):
        cmd = ['snmpwalk', '-Oe', '-On', '-v', vern, '-c', comm, host, oid]
        return cls.subcall(cmd)
