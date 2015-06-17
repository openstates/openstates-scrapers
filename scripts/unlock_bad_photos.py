#!/usr/bin/env python
# Unlock any non-200'ish photo URLs for a state

import sys
import requests
from billy.core import db


def unlock(person):
    if not person.get("photo_url"):
        return

    locked = person.get('_locked_fields')
    if locked is None or 'photo_url' not in locked:
        # We're not locked, so that's fine.
        return

    print("{_id} - {photo_url}".format(**person))

    # Count redirects as 404s because their 404 page (which says 404 on it)
    # is actually a 200. TOOT TOOT.
    if requests.get(person['photo_url'], allow_redirects=False).status_code // 100 == 2:
        return

    # Right, we've got a photo_url, but it sucks. Let's go and unlock
    # and save this homie.

    print(" -> Unlocked!")
    locked.remove("photo_url")
    person['_locked_fields'] = locked
    db.legislators.save(person)


def main(state):
    for _ in map(unlock, db.legislators.find({"state": state})):
        pass


if __name__ == "__main__":
    main(*sys.argv[1:])
