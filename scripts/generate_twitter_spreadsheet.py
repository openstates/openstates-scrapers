'''
Module to generate a spreadsheet for Nina to enter twitter ids into.
leg_id	name id
------  ---- --
CAL12   Thom twneale
'''

import csv
from billy import db


if __name__ == '__main__':


	writer = csv.DictWriter(open('twitter_ids.csv', 'wb'),
							fieldnames=['id', 'full_name', 'twitter'])

	
	for abbr in 'de fl ga il io mt nb nh nd ri sd tn'.split():
	
		for leg in db.legislators.find({'state': abbr}):
			writer.writerow({'id': leg['_id'].encode('utf-8'), 
				             'full_name': leg['full_name'].encode('utf-8')})