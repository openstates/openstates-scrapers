#!/bin/bash

if [[ -z $1 ]]; then
    echo "Missing argument for scrape type"
    exit 1
fi
set -e

mysqld --user root --max_allowed_packet=512M &
/opt/openstates/openstates/scrapers/ca/download.sh
poetry run os-update ca $*
