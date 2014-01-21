'''Revise imaginary session 109 back to 108. This should be find because
all bills that got a "109" session value were actually scraped from the
108'th session.
'''
from billy.core import db

def main():

    # Select all votes that had awful 109 or "109" as session.
    spec = dict(state='tn', session={'$in': ['109', 109]})
    votes = db.votes.find(spec)

    for vote in votes:
        print(vote['session'])
        vote['session'] = '108'
        print('Setting vote to 108 on', vote['_id'])
        db.votes.save(vote, w=1)
        # import pdb; pdb.set_trace()


if __name__ == '__main__':
    main()