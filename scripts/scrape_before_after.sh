#!/usr/bin/env bash
# Scrape a jurisdiction on the base branch and on your working tree, then diff them.
#
#   scripts/scrape_before_after.sh <jurisdiction> [os-update args...]
#   scripts/scrape_before_after.sh tn bills session=114
#
# The base runs first, at the site's normal pace, and fills a page cache. Your
# working tree then replays that cache with --fastmode, so both sides parse the
# same pages and the diff shows what your change did, not what the site changed
# between the runs. Pages only your change requests are fetched live, unthrottled.
#
# Everything lands in _scrapes/<jurisdiction>/ (git-ignored):
#   before.zip, after.zip  scrape output, each with its log
#   report.md              scripts/compare_scrapes.py's report, headed by both commits
# Upload the two zips (drag them into the PR description, or attach them to a
# release on your fork) and link them from the PR as pre-data: and post-data:.
#
# Environment:
#   BASE=<ref>       compare against the merge base with this ref (default: main)
#   OS_UPDATE=<cmd>  the scrape command (default: poetry run os-update)
#   SHOW=<name>      also pass --show <name> to the report, e.g. SHOW="SB 602"
set -euo pipefail

if [ $# -lt 1 ]; then
  sed -n '2,/^set /p' "$0" | sed '$d; s/^# \{0,1\}//'
  exit 2
fi
juris=$1
shift

root=$(git rev-parse --show-toplevel)
cd "$root"
base=$(git merge-base "${BASE:-main}" HEAD)
head=$(git rev-parse HEAD)
dirty=$(git status --porcelain -- scrapers | grep -q . && echo " + uncommitted changes" || true)
read -r -a os_update <<< "${OS_UPDATE:-poetry run os-update}"

out=$root/_scrapes/$juris
rm -rf "$out"
mkdir -p "$out"
git worktree prune
git worktree add --detach "$out/base-src" "$base" > /dev/null
trap 'git worktree remove --force "$out/base-src"' EXIT

scrape() { # <before|after> <scrapers dir> [extra os-update flags...]
  local side=$1 src=$2
  shift 2
  echo "== $side: ${os_update[*]} $juris $ARGS --scrape $*" >&2
  PYTHONPATH=$src "${os_update[@]}" "$juris" ${args[@]+"${args[@]}"} --scrape \
    --cachedir "$out/cache" --datadir "$out/$side" "$@" 2>&1 | tee "$out/$side.log"
  (cd "$out/$side/$juris" && zip -qr "$out/$side.zip" .)
  zip -qj "$out/$side.zip" "$out/$side.log"
}

args=("$@")
ARGS="${args[*]:-}"
scrape before "$out/base-src/scrapers"
scrape after "$root/scrapers" --fastmode

show=()
[ -n "${SHOW:-}" ] && show=(--show "$SHOW")
{
  echo "Command: \`os-update $juris $ARGS --scrape\`"
  echo
  echo "- before: \`$(git rev-parse --abbrev-ref "${BASE:-main}")\` @ ${base:0:9} (merge base)"
  echo "- after: \`$(git rev-parse --abbrev-ref HEAD)\` @ ${head:0:9}$dirty, replaying the before run's cache"
  echo
  python3 scripts/compare_scrapes.py --pre "$out/before.zip" --post "$out/after.zip" "${show[@]+"${show[@]}"}"
} > "$out/report.md"

echo "Wrote $out/before.zip, $out/after.zip and $out/report.md" >&2
