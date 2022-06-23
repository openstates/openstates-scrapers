#!/usr/bin/env bash

set -eo pipefail

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

IMAGE_NAME=openstates-scrapers_scrape:latest

if [[ -z $* ]]; then
    echo "You must provide os-update commands to run"
    echo "e.g. usa votes year=2022"
    exit 1
fi

set -eo pipefail

docker buildx build "${SCRIPT_DIR}/../" --tag "${IMAGE_NAME}"

rm -rf "${SCRIPT_DIR}/../_scrapes/$(date +%Y-%m-%d)/" "${SCRIPT_DIR}/../_auto-people"

for scraper in $(jq -r '.[].people | .[]' < "${SCRIPT_DIR}/../jurisdiction_configs.json" | xargs); do
	docker run --rm \
	-v
	poetry run spatula scrape "${scraper}"
done

mkdir -p "${SCRIPT_DIR}/../_auto-people"

find "${SCRIPT_DIR}/../_scrapes/$(date +%Y-%m-%d)" -type f -name "*.json" -exec mv {} "${SCRIPT_DIR}/../_auto-people/" \;
