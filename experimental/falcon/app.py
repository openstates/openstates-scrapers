import sys
import codecs
import urllib
from billy.utils import db
from collections import defaultdict
from flask import Flask, render_template, request, redirect


app = Flask(__name__)
cached_all_response = ""


@app.route("/")
def index():
    return redirect("/view/il")


@app.route("/view/<state>")
def view(state=None):
    htmlargs = urllib.urlencode(request.args)
    argz = dict(request.args)
    return render_template('falcon.html', **{
        "state": state,
        "args": htmlargs
    })


def csv_response(spec, **kwargs):
    bills = db.bills.find(spec)
    counts = defaultdict(int)
    high_score = 0

    chamber = kwargs.get('chamber', [])
    types = kwargs.get('type', [])

    buf = "Date,Count,Pct\n"

    for bill in bills:
        for action in bill['actions']:
            date = action['date'].strftime("%Y-%m-%d")
            actor = action['actor']
            state = bill['state']
            typez = action['type']

            if chamber != [] and not actor in chamber:
                continue

            if types != []:
                found = False
                for t in typez:
                    if t in types:
                        found = True

                if not found:
                    continue

            key = "%s" % (
                date
            )
            counts[key] += 1
            if counts[key] > high_score:
                high_score = counts[key]

    for line in counts:
        date = line
        count = counts[line]
        buf += "%s,%s,%s\n" % (
            date, count, float(count) / float(high_score)
        )
    return buf


# print "Loading initial all response"
# print " (srsly, hang on)"
# print ""
# cached_all_response = csv_response({})
## Uncomment me if you're hitting `all' to show it off.
# print "Loaded."


@app.route("/csv/<state>")
def csv(state=None):
    spec = {
        "state": state
    }

    args = dict(request.args)

    if state == 'all' and args == {}:
        return cached_all_response
    return csv_response(spec, **args)

if __name__ == "__main__":
    app.debug = True
    app.run()
