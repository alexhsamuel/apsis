#!/usr/bin/bash

. $(dirname $0)/env.sh
ulimit -n 10240
$PROCSTAR_PATH --agent --log-level trace
