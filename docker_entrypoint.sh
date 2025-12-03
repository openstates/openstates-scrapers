#!/usr/bin/env bash
###
# Ensures any GOOGLE_APPLICATION_CREDENTIALS are correctly enabled
#
# Sometimes we want to be able to pass in Google Cloud Platform credentials as an environment variable,
# but GCP libraries look for this to be saved as a file and for the env var to be a filepath.
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

###
# Print external IP used: helpful for debugging connectivity/IP-based blocks
# both OS-level and requests library (in case requests is using proxy)
###
ip="$(curl -s --insecure -m 5 https://ipecho.net/plain)"
printf "OS-level external IP for this scraper run is: %s\n" "$ip"
poetry run python scripts/log_external_ip.py
echo "Keep in mind IP may not be stable from request to request if using a proxy"

# shellcheck disable=SC2048 disable=SC2086
poetry run os-update $*
