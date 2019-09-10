#!/bin/bash

strat=$1
date=$2

echo "opening $strat for $today"

echo "starting secmaster service"
sleep 30

echo "starting position service"
sleep 30

echo "starting risk service"
sleep 30

echo "starting order manager"
sleep 30

echo "starting trader"
sleep 30

echo "day is open"
echo $date > $(dirname $0)/../work/open_day.$strat

