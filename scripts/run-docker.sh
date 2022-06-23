#!/usr/bin/env bash

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
IMAGE_NAME=openstates-scrapers_scrape:latest

if [[ -z $* ]]; then
    echo "You must provide commands to run!"
    echo "e.g. os-update usa votes year=2022"
    exit 1
fi

set -eo pipefail

pushd "${SCRIPT_DIR}/../" > /dev/null 2>&1 || exit 1

docker buildx build . --tag "${IMAGE_NAME}"

docker run --rm \
    --user "$(id -u):$(id -g)" \
    -v "${SCRIPT_DIR}/../_data:/opt/openstates/openstates/_data" \
    -v "${SCRIPT_DIR}/../_cache:/opt/openstates/openstates/_cache" \
    -v "${SCRIPT_DIR}/../_scrapes:/opt/openstates/openstates/_scrapes" \
    "${IMAGE_NAME}" \
    "$@"
