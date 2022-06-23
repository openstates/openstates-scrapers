#!/usr/bin/env bash

set -eo pipefail

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
USE_DOCKER=${USE_DOCKER:-no}

# clean up processing folders
rm -rf "${SCRIPT_DIR}/../_scrapes/$(date +%Y-%m-%d)/" "${SCRIPT_DIR}/../_auto-people"

if [[ "${USE_DOCKER}" == "yes" ]]; then
    IMAGE_NAME=openstates-scrapers_scrape:latest

    docker buildx build "${SCRIPT_DIR}/../" --tag "${IMAGE_NAME}"

    for scraper in $(jq -r '.[].people | .[]' < "${SCRIPT_DIR}/../jurisdiction_configs.json" | xargs); do
        docker run --rm \
            -v "${SCRIPT_DIR}/../_scrapes:/opt/openstates/openstates/_scrapes" \
            "${IMAGE_NAME}" \
            spatula scrape "${scraper}"
    done
    docker run --rm \
        -v "${SCRIPT_DIR}/../_scrapes:/opt/openstates/openstates/_scrapes" \
        "${IMAGE_NAME}" \
        chmod -R go+rwx "/opt/openstates/openstates/_scrapes/$(date +%Y-%m-%d)/"
else
    for scraper in $(jq -r '.[].people | .[]' < "${SCRIPT_DIR}/../jurisdiction_configs.json" | xargs); do
        poetry run spatula scrape "${scraper}"
    done
fi

mkdir -p "${SCRIPT_DIR}/../_auto-people"

find "${SCRIPT_DIR}/../_scrapes/$(date +%Y-%m-%d)" -type f -name "*.json" -exec cp {} "${SCRIPT_DIR}/../_auto-people/" \;
rm -rf "${SCRIPT_DIR}/../_scrapes/$(date +%Y-%m-%d)"


