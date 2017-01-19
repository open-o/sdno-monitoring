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

'''
Interface for tornado
'''

import netflow as nf

# Collect log file from jnca
nf.lfp = LogFileProcessor("../../jnca", "../../jnca/bak0906")


def docmd_flow(calldic):
    request = calldic["request"]

    if request == "ms_flow_set_topo":
        return nf.ms_flow_set_topo(calldic)

    if request == "ms_flow_get_flow":
        return nf.ms_flow_get_flow(calldic)

    return "Bad request '%s'" % request
