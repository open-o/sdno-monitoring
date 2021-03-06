#!/bin/sh
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


BASEDIR=$(dirname "$0")
cd $BASEDIR

# For load libhilda.so
export LD_LIBRARY_PATH=.:$PATH

while [ 1 ]; do
    cd $(dirname $(readlink -f $0))

    export KLOG_DFCFG=/tmp/klog.snmp.dfcfg
    export KLOG_RTCFG=/tmp/klog.snmp.rtcfg

    touch /tmp/klog.snmp.dfcfg
    touch /tmp/klog.snmp.rtcfg

    ./snmp.py

    echo "sleep before next try"
    sleep 1
done
