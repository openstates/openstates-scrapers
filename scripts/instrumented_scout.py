#!/usr/bin/env python3

import sys
from spatula.cli import scout

states = [
    "ak",
    "al",
    "ar",
    "az",
    "ca",
    "co",
    "ct",
    "dc",
    "de",
    "fl",
    "ga",
    "hi",
    "ia",
    "id",
    "il",
    "in",
    "ks",
    "ky",
    "la",
    "ma",
    "md",
    "me",
    "mi",
    "mn",
    "mo",
    "ms",
    "mt",
    "nc",
    "nd",
    "ne",
    "nh",
    "nj",
    "nm",
    "nv",
    "ny",
    "oh",
    "ok",
    "or",
    "pa",
    "pr",
    "ri",
    "sc",
    "sd",
    "tn",
    "tx",
    "ut",
    "va",
    "vt",
    "wa",
    "wi",
    "wv",
    "wy",
]

if __name__ == "__main__":
    exceptions = {}

    for state in states:
        try:
            scout([f"scrapers_next.{state}.people", "-o", f"artifacts/{state}.json"])
        except SystemExit:
            pass
        except Exception as e:
            exceptions[state] = e
            print(f"got exception while running {state}")

    for state, exception in exceptions.items():
        print(f"Error running {state}:\n\t{exception}")
    if exceptions:
        sys.exit(1)
