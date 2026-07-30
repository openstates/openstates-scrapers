#!/usr/bin/env bash
#
# CodeBot test helper for openstates-scrapers.
#
# Runs this repo's real (small) unit test suite against THIS checkout (the
# clone CodeBot is editing), in an isolated, throwaway Docker container built
# from this repo's own Dockerfile — no Postgres/Redis needed (this repo's
# only working tests touch no DB, no network, no fixtures/cassettes) and no
# compose stack needed for the same reason.
#
# IMPORTANT — scoped to tests/ deliberately, NOT a bare `pytest`:
#   scrapers/il/tests/ contains legacy, Python-2-era tests (`from nose.tools
#   import *` — nose isn't even in this repo's poetry.lock — plus
#   str.decode() calls). setup.cfg's own flake8 config excludes this
#   directory for the same reason. A bare `pytest` run from repo root fails
#   at collection before it ever reaches a real test. Only tests/ (currently
#   tests/test_classify_motion.py) is a real, passing, Python-3-compatible
#   test file.
#
# This repo's own CI (.github/workflows/lint.yml) only runs flake8 + black
# --check, never pytest — so there is no existing "how CI tests this" recipe
# to mirror here; this script is this repo's first real automated-test
# runner, scoped to what's actually real and passing today.
#
# The devos `test-ticket` skill invokes this via the required `.codebot/test.sh`
# entrypoint (Step 0 of that skill looks for that exact path at the repo root).
#
# Usage:
#   .codebot/test.sh [TICKET_KEY] [extra pytest args/paths, still under tests/]
#
# Exit code is pytest's exit code (0 = all tests passed).

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

TICKET_KEY="${1:-run}"
shift || true
TEST_ARGS=("$@")
if [[ ${#TEST_ARGS[@]} -eq 0 ]]; then
  TEST_ARGS=(tests/)
fi

SAFE_KEY="$(echo "${TICKET_KEY}" | tr '[:upper:]' '[:lower:]' | tr -c 'a-z0-9' '-' | sed 's/-\{2,\}/-/g; s/^-//; s/-$//')"
# Image tag scoped by ticket key + PID, not a fixed shared name — CAMS's
# worker pool can run multiple CodeBot tickets concurrently.
IMAGE="codebot-openstates-scrapers-test:${SAFE_KEY:-run}-$$"

cleanup() {
  docker rmi "${IMAGE}" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo ">>> CodeBot isolated test run for ${TICKET_KEY} (openstates-scrapers)"
echo ">>> image=${IMAGE}"

echo ">>> building image from this checkout..."
docker build -q -t "${IMAGE}" "${REPO_ROOT}" >/dev/null

echo ">>> running: pytest ${TEST_ARGS[*]}"
# Override the image's own ENTRYPOINT (docker_entrypoint.sh, meant for the
# real scrape jobs) — this run only needs `poetry run pytest`.
docker run --rm --entrypoint poetry "${IMAGE}" run pytest "${TEST_ARGS[@]}"
