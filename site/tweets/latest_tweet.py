import json
import pymongo
from scrapelib import urlopen
from billy.core import settings

_latest_tweet = None

def get_latest_tweet():
    global _latest_tweet
    if not _latest_tweet:
        conn = pymongo.Connection(settings.MONGO_HOST, settings.MONGO_PORT)
        _latest_tweet = conn['openstates_web']['tweets'].find_one()
    return _latest_tweet

def main():
    conn = pymongo.Connection(settings.MONGO_HOST, settings.MONGO_PORT)
    tweets = conn['openstates_web']['tweets']
    data = urlopen('http://api.twitter.com/1/statuses/user_timeline.json?screen_name=openstates&count=1&trim_user=1')
    data = json.loads(data)
    tweets.drop()
    tweets.insert(data, safe=True)

if __name__ == '__main__':
    main()
