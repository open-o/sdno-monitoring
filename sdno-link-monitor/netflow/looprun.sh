#!/bin/sh

BASEDIR=$(dirname "$0")
cd $BASEDIR

# For load libhilda.so
export LD_LIBRARY_PATH=.:$PATH

while [ 1 ]; do
    cd $(dirname $(readlink -f $0))

    export KLOG_DFCFG=/tmp/klog.netflow.dfcfg
    export KLOG_RTCFG=/tmp/klog.netflow.rtcfg

    touch /tmp/klog.netflow.dfcfg
    touch /tmp/klog.netflow.rtcfg

    ./netflow.py

    echo "sleep before next try"
    sleep 1
done
