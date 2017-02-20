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
import shlex
import json
from functools import reduce

from dotdict import DotDict


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


def call_jsn_to_calldic(data):
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


def call_cmd_to_calldic(data):
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
            pairs.append(subsegs[0])
            pairs.append(subsegs[1])
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

            traceback.print_stack()

        return pairs

kvpair = KVPairs
