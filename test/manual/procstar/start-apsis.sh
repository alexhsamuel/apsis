#!/usr/bin/bash

. $(dirname $0)/env.sh
if [[ ! -f apsis.db ]]; then
    echo "creating apsis.db"
    apsisctl create apsis.db
fi

exec apsisctl --log DEBUG serve --config config.yaml

