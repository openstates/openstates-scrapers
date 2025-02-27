#!/usr/bin/env bash
###
# Entrypoint that sets up GOOGLE_APPLICATION_CREDENTIALS, if present
#
# This simple script:
# 1. ensures any GOOGLE_APPLICATION_CREDENTIALS are correctly enabled
# 2. Executes the actual CMD args passed to the container, using "poetry run os-update" as entrypoint
#
# Sometimes we want to be able to pass in Google Cloud Platform credentials as an environment variable,
# but GCP libraries look for this to be saved as a file and for the env var to be a filepath.
# Only intended to be used in docker containers
###
if [[ -n "${GOOGLE_APPLICATION_CREDENTIALS}" ]]; then
    echo "Applying app credentials..."
    echo "${GOOGLE_APPLICATION_CREDENTIALS}" > /creds.json
    GOOGLE_APPLICATION_CREDENTIALS="/creds.json"
    export GOOGLE_APPLICATION_CREDENTIALS
elif [[ -n "${GOOGLE_CREDENTIAL_FILE}" ]]; then
    echo "Assuming a valid credentials file is mounted at ${GOOGLE_CREDENTIAL_FILE}..."
    GOOGLE_APPLICATION_CREDENTIALS=${GOOGLE_CREDENTIAL_FILE}
    export GOOGLE_APPLICATION_CREDENTIALS
fi

# shellcheck disable=SC2048 disable=SC2086
poetry run os-update $*
