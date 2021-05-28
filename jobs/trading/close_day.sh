#!/bin/bash

strat=$1
date=$2
file=$(dirname $0)/../../work/open_day.$strat

if [[ ! -f $file ]]; then
    echo "day is not open" >&2
    exit 1
fi

open_date=$(cat $file)
if [[ $open_date != $date ]]; then
    echo "wrong date; open for $open_date" >&2
    exit 1
fi

echo "closing $strat for $today"

echo "stopping trader"
sleep 5

echo "stopping order manager"
sleep 10

echo "stopping risk service"
sleep 10

echo "stopping position service"
sleep 10

echo "stopping secmaster service"
sleep 10

echo "day is closed"
rm $file

