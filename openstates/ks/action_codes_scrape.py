#!/usr/bin/env python

import re
import ksapi

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
new_numbers = {}

def parse_action_codes(action_codes) :
	with open(action_codes) as action_codes:
		action_codes_str = action_codes.read()
	for line in action_codes_str.split('\n'):
		if comment.match(line):
			continue
		if data.match(line):
			match = data.match(line)
			number = match.group(1)
			if number not in ksapi.action_codes:
				print "New number: %s" % number
				new_numbers[number] ="new"

			numbers.append(number)
			if voted.match(match.group(2)):
				voted_codes.append(number)
			elif passed.match(match.group(2)):
				passed_codes.append(number)
			elif failed.match(match.group(2)):
				failed_codes.append(number)
			else:
				print "No rule %s" % line

		else :
			print "No match %s" % line

def report () :
	print("voted = %s" % voted_codes)
	print("passed = %s" % passed_codes)
	print("failed = %s" % failed_codes)


if __name__ == '__main__':
	parse_action_codes('action_codes')
	report ()
