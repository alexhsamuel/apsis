#!/usr/bin/bash

. $(dirname $0)/env.sh
ulimit -n 10240
exec $PROCSTAR_PATH --agent --log-level trace
