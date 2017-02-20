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
import frame
import fcntl


def AppSingleton(pid_file, message=None):
    '''Singleton for Application'''

    g = frame.frame(-1).f_globals

    fp = open(pid_file, 'w')
    g["singleton_fp"] = fp
    try:
        fcntl.lockf(fp, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except IOError:
        print(message or "Another instance exist, quit now")
        os._exit(0)


class ClsSingleton(type):
    ''' Singleton for Class

    add ```__metaclass__ = ClsSingleton``` to first line of class
    '''

    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(
                ClsSingleton, cls).__call__(
                *args, **kwargs)
        return cls._instances[cls]
