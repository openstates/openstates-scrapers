from jinja2 import Template
import jsindex


templates = {

    'committees': Template(
        '{{obj.committee}} {{obj.subcommittee}}'),

    'legislators': Template(
        '{{obj.full_name}} {{obj.district}} {{obj.party}}'),

    'bills': Template('''
        {{obj.bill_id}} {{obj.title}}
        {% for subject in obj.subjects %}
            {{ subject }}
        {% endfor %}
        ''')
    }

if __name__ == '__main__':
    from billy.models import db
    index = jsindex.IndexBuilder()

    cname = 'legislators'
    storekeys = ['full_name', '_type', 'chamber', 'district', 'party',
                 'state', '_id', 'photo_url']
    coll = getattr(db, cname)
    spec = {'state': 'ca', 'active': True}
    objects = coll.find(spec)
    print 'adding', objects.count(), cname, 'with spec %r' % spec
    renderer = lambda obj: templates[cname].render(obj=obj)
    index.add(cname[0], objects, renderer, all_substrs=True, storekeys=storekeys)

    cname = 'committees'
    storekeys = ['committee', 'chamber', '_type', 'state', '_id', 'members']
    coll = getattr(db, cname)
    spec = {'state': 'ca'}
    objects = coll.find(spec)
    print 'adding', objects.count(), cname, 'with spec %r' % spec
    renderer = lambda obj: templates[cname].render(obj=obj)
    index.add(cname[0], objects, renderer, all_substrs=True, storekeys=storekeys)

    spec.update(session='20112012')
    storekeys = ['bill_id', 'title', '_type', 'subjects', 'type', 'scraped_subjects',
                 'state', '_id', 'session']
    objects = db.bills.find(spec)
    print 'adding', objects.count(), 'bills', 'with spec %r' % spec
    renderer = lambda obj: templates['bills'].render(obj=obj)
    index.add('b', objects, renderer, substrs=True, storekeys=storekeys)

    jd = index.jsondata()
    js = index.as_json(showsizes=True)
    with open('index.json', 'w') as f:
        index.dump(f)
