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

from singleton import ClsSingleton


class LogTan_Null():
    __metaclass__ = ClsSingleton

    @classmethod
    def cfg(cls, **kwargs):
        pass

    def i(cls, rec, mod=None):
        pass

    def w(cls, rec, mod=None):
        pass

    def e(cls, rec, mod=None):
        pass

    def f(cls, rec, mod=None):
        pass

logtan = LogTan_Null()


def cfg(**kwargs):
    logtan.cfg(**kwargs)


def i(mod=None, **kwargs):
    logtan.i(rec, mod)


def w(mod=None, **kwargs):
    logtan.w(rec, mod)


def e(mod=None, **kwargs):
    logtan.e(rec, mod)


def f(mod=None, **kwargs):
    logtan.f(rec, mod)

