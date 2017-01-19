#!/usr/bin/env python
# encoding: utf-8
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
import socket
import collections
import time
import socket
import traceback

from struct import unpack

from bprint import varprt, varfmt
from xlogger import klog

def hexdump(s):
    return ":".join("{:02x}".format(ord(c)) for c in s)


HdrV5 = collections.namedtuple("HdrV5",
        'version count sysup_time unix_secs unix_nsecs flow_sequence engine_type engine_id sampling'
        )

RecV5 = collections.namedtuple("RecV5",
        '''
        src_addr_a
        src_addr_b
        src_addr_c
        src_addr_d
        dst_addr_a
        dst_addr_b
        dst_addr_c
        dst_addr_d
        nexthop_a
        nexthop_b
        nexthop_c
        nexthop_d
        in_if out_if packets octets first last src_port dst_port pad1 tcp_flags ip_proto tos src_as dst_as src_mask dst_mask pad2'''
        )

HdrV9 = collections.namedtuple("HdrV9",
        'version count sysup_time unix_secs pkg_sequence source_id'
        )

FlowSetHdr = collections.namedtuple("FlowSetHdr",
        'flowset_id length'
        )

# Template Record
TemplRecHdr = collections.namedtuple("TemplRecHdr",
        'templ_id field_count'
        )
TemplRecItem = collections.namedtuple("TemplRecItem",
        'type length'
        )

# Data Record
DataFlowSet = collections.namedtuple("DataFlowSet",
        'flowset_id length'
        )
DataRec = collections.namedtuple("DataRec",
        'flowset_id length'
        )


'''
flowset_id:
    0: template flowset
    1: options flowset
    > 255: data flow and flowset_id == templ_id

Templ = [
        typeidx, # size
        typeidx, # size
        typeidx, # size
        typeidx, # size
        typeidx, # size
        ]

'''

class NFServer(object):
    def __init__(self, port=2055, onflow=None):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(('', port))

        # templid@host <> body
        self.templmap = {}

        self.set_onflow(onflow)

    def set_onflow(self, onflow):
        self.onflow = onflow

    def run(self):
        while 1:
            try:
                data, address = self.sock.recvfrom(8192)
                self._on_recive(data, address)
            except (KeyboardInterrupt, SystemExit):
                raise
            except:
                traceback.print_exc()

    def _on_recive(self, data, address):
        ver, = unpack(">H", data[:2])
        klog.d("Found a package: Version: ", ver)

        if ver == 5:
            return self._on_pkg_v5(data, address)
        if ver == 9:
            return self._on_pkg_v9(data, address)

    def _on_pkg_v9(self, data, address):
        ##
        ## Header
        ##

        ## u_int16_t version;
        ## u_int16_t count;
        ## u_int32_t sysup_time;
        ## u_int32_t unix_secs;
        ## u_int32_t pkg_sequence;
        ## u_int32_t source_id;

        fmt = '>HHIIII'
        hdr = HdrV9(*unpack(fmt, data[:20]))


        ##
        ## FlowSet
        ##

        ofs = 24
        reclen = 48

        for i in range(hdr.count):
            fmt = '>HH'
            fshdr = FlowSetHdr(*unpack(fmt, data[ofs:ofs + reclen]))

            if fshdr.flowset_id == 0:
                # fshdr.length = fullsize of template

                # templid, fieldcnt =
                fmt = ">HH"
                hdr = TemplRecHdr(*unpack(fmt, data[ofs:ofs + reclen]))

                # segs = (type, len, type, len, ..., type, len)
                fmt = ">" + "H" * hdr.field_count
                segs = unpack(fmt, data[ofs:ofs + reclen])

                # todo: parse templ and save to templmap
                tempkey = "%d@%s" % (hdr.templ_id, address)

                recfmt = "Generate and save the fmt"
                # reclen = Calculate the record size
                self.templmap[tempkey] = [segs, recfmt, reclen]

            elif fshdr.flowset_id == 1:
                pass
            elif fshdr.flowset_id > 255:
                pass
                fmt = ">HH"
                flowsetid, length = unpack(fmt, data[ofs:ofs + reclen])

                tempkey = "%d@%s" % (flowsetid, address)
                segs, recfmt, reclen = self.templmap.get(tempkey, (None, None, None))
                if segs:
                    segs = unpack(recfmt, data[ofs:ofs + reclen])


            ofs += reclen


    def _on_pkg_v5(self, data, address):
        ##
        ## Header
        ##

        ## u_int16_t version;
        ## u_int16_t count;
        ## u_int32_t sysup_time;
        ## u_int32_t unix_secs;
        ## u_int32_t unix_nsecs;
        ## u_int32_t flow_sequence;
        ## u_int8_t engine_type;
        ## u_int8_t engine_id;
        ## u_int16_t sampling;

        fmt = '>HHIIIIBBH'
        hdr = HdrV5(*unpack(fmt, data[:24]))
        klog.d(varfmt(hdr, color=True))


        ##
        ## Record
        ##

        ofs = 24
        reclen = 48
        for i in range(hdr.count):
            ## struct in_addr src_addr;
            ## struct in_addr dst_addr;
            ## struct in_addr nexthop;
            ## u_int16_t in_if;
            ## u_int16_t out_if;
            ## u_int32_t packets;
            ## u_int32_t octets;
            ## u_int32_t first;
            ## u_int32_t last;
            ## u_int16_t src_port;
            ## u_int16_t dst_port;
            ## u_int8_t pad1;
            ## u_int8_t tcp_flags;
            ## u_int8_t ip_proto;
            ## u_int8_t tos;
            ## u_int16_t src_as;
            ## u_int16_t dst_as;
            ## u_int8_t src_mask;
            ## u_int8_t dst_mask;
            ## u_int16_t pad2;

            fmt = '>BBBBBBBBBBBBHHIIIIHHBBBBHHBBH'
            rec = RecV5(*unpack(fmt, data[ofs:ofs + reclen]))
            klog.d(varfmt(rec, color=True))
            ofs += reclen

            if self.onflow:
                segs = []
                segs.append(address[0])
                segs.append(time.strftime("%Y-%m-%d %H:%M:%S"))
                segs.append("%d.%d.%d.%d" % (rec.src_addr_a, rec.src_addr_b, rec.src_addr_c, rec.src_addr_d))
                segs.append("%d.%d.%d.%d" % (rec.dst_addr_a, rec.dst_addr_b, rec.dst_addr_c, rec.dst_addr_d))
                segs.append("%d.%d.%d.%d" % (rec.nexthop_a, rec.nexthop_b, rec.nexthop_c, rec.nexthop_d))
                segs.append(rec.packets)
                segs.append(rec.octets)
                segs.append(rec.src_mask)
                segs.append(rec.dst_mask)
                segs.append(rec.out_if)
                segs.append(rec.in_if)
                segs.append(rec.src_port)
                segs.append(rec.dst_port)
                segs.append("5")


                log = ""
                log += "NEWLOG: %s: " % address[0]
                log += "%d.%d.%d.%d " % (rec.src_addr_a, rec.src_addr_b, rec.src_addr_c, rec.src_addr_d)
                log += ">> "
                log += "%d.%d.%d.%d " % (rec.nexthop_a, rec.nexthop_b, rec.nexthop_c, rec.nexthop_d)
                log += ">> "
                log += "%d.%d.%d.%d " % (rec.dst_addr_a, rec.dst_addr_b, rec.dst_addr_c, rec.dst_addr_d)
                log += "*********"

                klog.d(log)

                self.onflow(address[0], rec)

if __name__ == "__main__":
    server = NFServer(2055)
    server.run()
