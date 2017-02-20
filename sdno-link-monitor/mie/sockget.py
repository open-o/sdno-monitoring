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

import socket


def sockget(s, length):
    '''Read socket till length reached or connection closed'''

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
