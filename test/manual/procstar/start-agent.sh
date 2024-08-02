#!/usr/bin/bash

. $(dirname $0)/env.sh
$PROCSTAR_PATH --agent --log-level trace
