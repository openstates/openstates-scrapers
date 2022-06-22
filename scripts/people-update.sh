#!/usr/bin/env bash

set -xeo pipefail

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

rm -rf "${SCRIPT_DIR}/../_scrapes/$(date +%Y-%m-%d)/" "${SCRIPT_DIR}/../_auto-people"

for scraper in $(jq -r '.[].people | .[]' < "${SCRIPT_DIR}/../jurisdiction_configs.json" | xargs); do
    poetry run spatula scrape "${scraper}"
done

mkdir -p "${SCRIPT_DIR}/../_auto-people"

find "${SCRIPT_DIR}/../_scrapes/$(date +%Y-%m-%d)" -type f -name "*.json" -exec mv {} "${SCRIPT_DIR}/../_auto-people/" \;
