#!/usr/bin/env bash

set -eo pipefail

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
OPENSSL_CONF="${SCRIPT_DIR}/../openssl.cnf"
export OPENSSL_CONF
TODAY=$(date +%Y-%m-%d)

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
rm -rf "${SCRIPT_DIR}/../_scrapes/${TODAY}"

echo "Cloning people repo..."
REPO_FOLDER=/tmp/people-git
rm -rf "${REPO_FOLDER}"
git clone git@github.com:openstates/people.git "${REPO_FOLDER}"
pushd "${REPO_FOLDER}" > /dev/null || exit 1
git checkout -b "${TODAY}-auto-people-merge"
popd > /dev/null || exit 1

for scraper in ${JURISDICTIONS}; do
    poetry run spatula scrape "${scraper}" | tee "${SCRIPT_DIR}/../_scrapes/${TODAY}-scrape.tmp"
	ABBR=$(echo "${scraper}" | cut -d"." -f2)
	FOLDER="${SCRIPT_DIR}/../$(tail -1 "${SCRIPT_DIR}/../_scrapes/${TODAY}-scrape.tmp" | rev | cut -d" " -f1 | rev)"
	rm -f "${SCRIPT_DIR}/../_scrapes/${TODAY}-scrape.tmp"
	echo "Syncing from ${FOLDER} to ${REPO_FOLDER}..."
	OS_PEOPLE_DIRECTORY="${REPO_FOLDER}" poetry run os-people merge "${ABBR}" "${FOLDER}"
done

rm -rf "${SCRIPT_DIR}/../_scrapes/${TODAY}"
