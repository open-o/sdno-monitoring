#!/bin/sh

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
