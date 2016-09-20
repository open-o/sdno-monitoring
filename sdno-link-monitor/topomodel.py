#!/usr/bin/python
# -*- coding: utf-8 -*-
#
#  Copyright (c) 2016, China Telecommunication Co., Ltd.
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

import json
from base_handler import base_model



class equipment(base_model):
    '''
    router equipment model
    '''

    def __init__(self):
        super(equipment,self).__init__()
        self.uid = ''
        self.name = ''
        self.model = ''
        self.community = ''
        self.vendor = ''
        self.x = 0.0
        self.y = 0.0
        self.pos = ''
        self.ip_str = ''
        self.ports = []

    def set_attrib(self, name, val):
        if name in self.__dict__:
            object.__setattr__(self, name, val)
        pass



class vlink(base_model):
    def __init__(self):
        super(vlink, self).__init__()
        self.uid = ''
        self.sequip = ''
        self.dequip = ''
        self.bandwidth = 0.0    # in Mbps unit.
        self.percentage = 0.0
        self.sport = ''
        self.dport = ''
        self.delay = 0
        pass

    pass

class topo(base_model):
    def __init__(self):
        super(topo,self).__init__()
        self.equip = []
        self.vlink = []

    pass



if __name__ == '__main__':
    eq = equipment()
    rt = {'uid':'abc123', 'name':'core1', 'model':'P1200', 'vendor':'cisco', 'community':'a-z', 'x':10.1, 'y':2.5, 'pos':'xicheng'}
    for k in rt.keys():
        eq.set_attrib(k, rt[k])

    print eq



