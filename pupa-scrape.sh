#!/bin/sh

PYTHONPATH=./openstates poetry run pupa ${PUPA_ARGS:-} update "$@"
