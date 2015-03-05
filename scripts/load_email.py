#!/usr/bin/env python
import itertools
import sys
import csv

with open(sys.argv[1], 'r') as fd:
    d = csv.DictReader(fd)
    for row in d:
        print(row['leg_id'])
