from flask import Flask, render_template, request
from billy.core import settings, db
from pymongo import Connection

connection = Connection('localhost', 27017)
nudb = connection.harpy

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html", **{
        "subjects": settings.BILLY_SUBJECTS
    })


@app.route("/who")
def who():
    subject = request.args.get('subject', '')
    yinz = nudb.interests.find({"subjects.%s" % (subject): {"$exists": True}})
    els = [(x, db.legislators.find_one(x['_id'])) for x in yinz]
    return render_template('who.html', els=els)


if __name__ == '__main__':
    app.run(debug=True)
