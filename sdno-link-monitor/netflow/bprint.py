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

'''
Beatiful print ojbect
'''

import sys
import json

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

    if title is not None:
        f = sys._getframe(lvl)
        ln = f.f_lineno
        fn = f.f_code.co_filename

        title = "%s |%s:%d" % (title, fn, ln)
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
    elif hasattr(obj, "__dict__"):
        data = dict([(key, todict(value, classkey))
                     for key, value in obj.__dict__.iteritems()
                     if not callable(value) and not key.startswith('_')])
        if classkey is not None and hasattr(obj, "__class__"):
            data[classkey] = obj.__class__.__name__
        return data
    elif hasattr(obj, "__iter__"):
        return [todict(v, classkey) for v in obj]
    else:
        return obj


def varprt(obj, title=None):
    printb(todict(obj), title, lvl=3)


def varfmt(obj, title=None):
    return formatb(todict(obj), title, lvl=2)


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

    r = red
    g = green
    y = yellow
    b = blue
    p = purple
    c = cyan
    h = gray

cp = ColorPrint
