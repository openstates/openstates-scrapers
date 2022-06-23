#!/usr/bin/env bash

set -eo pipefail

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
OPENSSL_CONF="${SCRIPT_DIR}/../openssl.cnf"
export OPENSSL_CONF

# get a list of all configured jurisdictions for this tool
JUR_NAMES=$(jq -r .[].name < "${SCRIPT_DIR}/../jurisdiction_configs.json" | xargs)

# if we supply specific jurisdictions...
if [[ -n "$@" ]]; then
    NAMES=$(echo "$@" | tr ' ' '|')
    JURISDICTIONS=$(jq --arg n "${NAMES}" -r '.[] | select(.name | test($n)) | .people // [] | .[]' < "${SCRIPT_DIR}/../jurisdiction_configs.json" | xargs)
# otherwise we should collect them all
else
    JURISDICTIONS=$(jq -r '.[].people // [] | .[]' < "${SCRIPT_DIR}/../jurisdiction_configs.json" | xargs)
fi

# clean up processing folders
rm -rf "${SCRIPT_DIR}/../_scrapes/$(date +%Y-%m-%d)/" "${SCRIPT_DIR}/../_auto-people"

for scraper in ${JURISDICTIONS}; do
    poetry run spatula scrape "${scraper}"
done

mkdir -p "${SCRIPT_DIR}/../_auto-people"

if [[ ! -d "${SCRIPT_DIR}/../_scrapes/$(date +%Y-%m-%d)" ]]; then
    echo "No output generated!"
    exit 1
fi
find "${SCRIPT_DIR}/../_scrapes/$(date +%Y-%m-%d)" -type f -name "*.json" -exec cp {} "${SCRIPT_DIR}/../_auto-people/" \;
rm -rf "${SCRIPT_DIR}/../_scrapes/$(date +%Y-%m-%d)"

