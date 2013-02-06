import requests
import csv
import json
import glob

urls = ('http://ec2-184-73-61-66.compute-1.amazonaws.com/boundaries/sldu/?limit=20000',
        'http://ec2-184-73-61-66.compute-1.amazonaws.com/boundaries/sldl/?limit=20000')
boundaries = set()
for url in urls:
    resp = json.loads(requests.get(url).content)
    for obj in resp['objects']:
        boundaries.add(obj['url'].replace('/boundaries/', '').rstrip('/'))

csv_boundaries = set()
for file in glob.glob('manual_data/districts/*.csv'):
    file = csv.DictReader(open(file))
    for line in file:
        csv_boundaries.add(unicode(line['boundary_id']))

print 'Districts appearing only in the boundary API:'
for b in boundaries-csv_boundaries:
    if 'not-defined' not in b:
        print '  ', b

print 'Districts not appearing in the boundary API:'
for b in csv_boundaries-boundaries:
    print '  ', b
