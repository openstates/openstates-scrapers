#!/usr/bin/env python
from couchdb.schema import Document, TextField, ListField, View

class Legislator(Document):
    fullname = TextField()
    first_name = TextField()
    last_name = TextField()
    middle_name = TextField()
    suffix = TextField()
    party = TextField()
    chamber = TextField()
    district = TextField()
    sessions = ListField(TextField())
