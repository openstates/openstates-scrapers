#!/usr/bin/env python

import re

data = re.compile(r'^([a-z]+_[a-z]+_[0-9]{3}): (.*) *$')
comment = re.compile(r'^#')
variable = re.compile(r'\$([a-z_]+)\$')

voted = re.compile(r'.*\$vote_tally\$.*')
passed = re.compile(r'.*(?!not )(passed|adopted).*\$vote_tally\$.*', re.IGNORECASE)
failed = re.compile(r'.*(failed|not adopted|not passed).*\$vote_tally\$.*', re.IGNORECASE)

voted_codes = []
passed_codes = []
failed_codes = []
numbers = []

with open('action_codes') as action_codes:
	action_codes_str = action_codes.read()
	for line in action_codes_str.split('\n'):
		if comment.match(line):
			continue
		if data.match(line):
			match = data.match(line)
			number = match.group(1)
			numbers.append(number)
			if voted.match(match.group(2)):
				voted_codes.append(number)
			if passed.match(match.group(2)):
				passed_codes.append(number)
			if failed.match(match.group(2)):
				failed_codes.append(number)

print("voted = %s" % voted_codes)
print("passed = %s" % passed_codes)
print("failed = %s" % failed_codes)

