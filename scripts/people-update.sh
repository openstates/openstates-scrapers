#!/usr/bin/env bash

set -eo pipefail

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
OPENSSL_CONF="${SCRIPT_DIR}/../openssl.cnf"
export OPENSSL_CONF
TODAY=$(date +%Y-%m-%d)

# exclusive filter (don't run these)
SKIP_JURISDICTIONS=${SKIP_JURISDICTIONS:-}
# inclusive filter (only run these)
SPECIFIC_JURISDICTIONS=${SPECIFIC_JURISDICTIONS:-}

# if we supply specific jurisdictions...
if [[ -n "${SPECIFIC_JURISDICTIONS}" ]]; then
    NAMES=$(echo "${SPECIFIC_JURISDICTIONS}" | tr ',' '|')
    JURISDICTIONS=$(jq --arg n "${NAMES}" -r '.[] | select(.name | test($n)) | .people // [] | .[]' < "${SCRIPT_DIR}/../jurisdiction_configs.json" | xargs)
elif [[ -n "${SKIP_JURISDICTIONS}" ]]; then
    NAMES=$(echo "${SKIP_JURISDICTIONS}" | tr ',' '|')
    JURISDICTIONS=$(jq --arg n "${NAMES}" -r '.[] | select(.name | test($n)|not) | .people // [] | .[]' < "${SCRIPT_DIR}/../jurisdiction_configs.json" | xargs)
# otherwise we should collect them all
else
    JURISDICTIONS=$(jq -r '.[].people // [] | .[]' < "${SCRIPT_DIR}/../jurisdiction_configs.json" | xargs)
fi

# clean up processing folders
rm -rf "${SCRIPT_DIR}/../_scrapes/${TODAY}"
mkdir -p "${SCRIPT_DIR}/../_scrapes"

echo "ensuring depdendencies are up to date"
poetry install

echo "Cloning people repo..."
REPO_FOLDER=/tmp/people-git
rm -rf "${REPO_FOLDER}"
git clone git@github.com:openstates/people.git "${REPO_FOLDER}"
pushd "${REPO_FOLDER}" > /dev/null || exit 1
git checkout -b "${TODAY}-auto-people-merge"
popd > /dev/null || exit 1

for scraper in ${JURISDICTIONS}; do
    poetry run spatula scrape "${scraper}" | tee "${SCRIPT_DIR}/../_scrapes/${TODAY}-scrape.tmp"
	# last portion of the scraper name will be the jurisdiction abbreviation
	ABBR=$(echo "${scraper}" | cut -d"." -f2)
	# the last line of output in a scrape indicates the relative folder path where data lives
	FOLDER="${SCRIPT_DIR}/../$(tail -1 "${SCRIPT_DIR}/../_scrapes/${TODAY}-scrape.tmp" | rev | cut -d" " -f1 | rev)"
	rm -f "${SCRIPT_DIR}/../_scrapes/${TODAY}-scrape.tmp"
	echo "Syncing from ${FOLDER} to ${REPO_FOLDER}..."
	OS_PEOPLE_DIRECTORY="${REPO_FOLDER}" poetry run os-people merge "${ABBR}" "${FOLDER}" --reset-offices
done

rm -rf "${SCRIPT_DIR}/../_scrapes/${TODAY}"

# Show local changes
pushd "${REPO_FOLDER}" > /dev/null || exit 1
git add *
# make sure all output is printed and we exit the diff screen
echo | git diff
# commit and push data to new branch
git commit -as -m "${TODAY} full people update"
git push --set-upstream origin "${TODAY}-auto-people-merge"
popd > /dev/null || exit 1

rm -rf "${REPO_FOLDER}"
