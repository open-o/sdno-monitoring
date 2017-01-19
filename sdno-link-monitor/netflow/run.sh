#!/bin/bash
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

MSB_ADDRESS="msb.openo.org:8086"
SDNO_MONITORING_ADDRESS="sdno-monitoring:8610"

PROC_UNIQ_KEY=e6308869-938e-46d9-b04d-4b87f6847962
BASEDIR=$(dirname $(readlink -f $0))

OPTS=""
OPTS+=" --uniq=${PROC_UNIQ_KEY}"
OPTS+=" --msburl=${MSB_ADDRESS}"
OPTS+=" --localurl=${SDNO_MONITORING_ADDRESS}"

nohup python ${BASEDIR}/netflow.py ${OPTS} &> /dev/null &
