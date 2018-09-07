#!/bin/sh

set -e

# Set up Google service account credentials if provided via environment var
#
# @see https://cloud.google.com/logging/docs/agent/authorization
# @see http://google-cloud-python.readthedocs.io/en/latest/core/auth.html
if [ ! -z ${GOOGLE_CLOUD_CREDENTIALS+x} ]; then
  export GOOGLE_APPLICATION_CREDENTIALS="/etc/google/auth/application_default_credentials.json"
  mkdir -p /etc/google/auth
  echo "$GOOGLE_CLOUD_CREDENTIALS" > "$GOOGLE_APPLICATION_CREDENTIALS"
  chown root:root "$GOOGLE_APPLICATION_CREDENTIALS"
  chmod 0400 "$GOOGLE_APPLICATION_CREDENTIALS"
fi

#PUPA_ENV=~/.virtualenvs/pupa
#BILLY_ENV=~/.virtualenvs/openstates

# copy use shift to get rid of first param, pass rest to pupa update
state=$1
shift

# The gentleman's delivery/deployment hehe
#
# NOTE: noop the git pull call in case it fails
# @see https://stackoverflow.com/a/40650331/1858091
( cd /opt/openstates/openstates && \
  git stash && \
  ( git pull origin govhawk-deploy || : ) ) > /dev/null

export PYTHONPATH=./openstates

$PUPA_ENV/bin/pupa ${PUPA_ARGS:-} update $state "$@"

if [ "$SKIP_BILLY" = true ]; then
  exit 0
fi

export PUPA_DATA_DIR='../openstates/_data'
export PYTHONPATH=./billy_metadata/
$BILLY_ENV/bin/python -m pupa2billy.run $state
$BILLY_ENV/bin/billy-update $state --import --report
