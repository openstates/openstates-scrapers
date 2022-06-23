#!/usr/bin/env bash

set -eo pipefail

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
USE_DOCKER=${USE_DOCKER:-no}

if [[ "${USE_DOCKER}" == "yes" ]]; then
    IMAGE_NAME=openstates-scrapers_scrape:latest

    docker buildx build "${SCRIPT_DIR}/../" --tag "${IMAGE_NAME}"

    rm -rf "${SCRIPT_DIR}/../_scrapes/$(date +%Y-%m-%d)/" "${SCRIPT_DIR}/../_auto-people"

    for scraper in $(jq -r '.[].people | .[]' < "${SCRIPT_DIR}/../jurisdiction_configs.json" | xargs); do
        docker run --rm \
        --user "$(id -u):$(id -g)" \
        -v "${SCRIPT_DIR}/../_scrapes:/opt/openstates/openstates/_scrapes" \
        "${IMAGE_NAME}" \
        spatula scrape "${scraper}"
    done
else
    for scraper in $(jq -r '.[].people | .[]' < "${SCRIPT_DIR}/../jurisdiction_configs.json" | xargs); do
        poetry run spatula scrape "${scraper}"
    done
fi

mkdir -p "${SCRIPT_DIR}/../_auto-people"

find "${SCRIPT_DIR}/../_scrapes/$(date +%Y-%m-%d)" -type f -name "*.json" -exec mv {} "${SCRIPT_DIR}/../_auto-people/" \;
