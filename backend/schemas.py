#!/usr/bin/env python
from couchdb.schema import *

# Some of the code in this file relies on patches I've made to couchdb-python.
# They've been submitted upstream but until they're applied you can grab
# them from:
# http://code.google.com/p/couchdb-python/issues/detail?id=76
# http://code.google.com/p/couchdb-python/issues/detail?id=77

class FiftyStateDocument(Document):

    @classmethod
    def all(cls, db, limit=200):
        """
        Returns an iterator for all of the documents of this type,
        grabbing 'limit' documents from the database at a time.
        """
        type = cls.type.default
        results = cls.view(db, 'app/by-type', limit=limit,
                           include_docs=True, eager=True)[type]

        while len(results) > 0:
            id = None
            for doc in results:
                yield doc
                id = doc.id
            results = cls.view(db, '_all_docs', include_docs=True,
                               eager=True, startkey=id,
                               skip=1)[type]


class StateMetadata(FiftyStateDocument):
    type = TextField(default='state_metadata')
    state_name = TextField()
    legislature_name = TextField()
    lower_chamber_name = TextField()
    upper_chamber_name = TextField()
    lower_title = TextField()
    upper_title = TextField()
    lower_term = IntegerField()
    upper_term = IntegerField()
    sessions = ListField(TextField())
    session_details = DictField()

    @classmethod
    def get(cls, db):
        # There should only be one document of this type, named state_medata
        return cls.load(db, 'state_metadata')

    def sessions_adjacent(self, session1, session2):
        """
        Returns true if session1 and session2 ocurred consecutively (in
        either order).
        """
        if session1 in self.sessions:
            index = self.sessions.index(session1)
            if index > 0 and self.sessions[index - 1] == session2:
                return True
            if ((index + 1) < len(self.sessions) and
                self.sessions[index + 1] == session2):
                return True
        return False

    def session_for_election(self, election_year):
        """
        Given an election year, return the subsequent session (or
        None if election_year is not a valid election year)
        """
        session = None
        for (s, details) in self.session_details.items():
            if details['years'][0] == election_year + 1:
                session = s
                break
        return session


class Legislator(FiftyStateDocument):
    type = TextField(default='legislator')
    state = TextField()
    full_name = TextField()
    first_name = TextField()
    last_name = TextField()
    middle_name = TextField()
    suffix = TextField()
    party = TextField()
    chamber = TextField()
    district = TextField()
    sessions = ListField(TextField())

    @classmethod
    def for_session(cls, db, session):
        """
        Return all the Legislators who served in a given session.
        """
        return cls.view(db, 'app/leg-by-session', include_docs=True,
                        eager=True, startkey=[session, None, None],
                        endkey=[session, "zzzzzzzz", None])

    @classmethod
    def duplicates(cls, db, chamber, district, full_name):
        """
        Return all legislators which match the given chamber,
        district and full name.
        """
        return cls.view(db, 'app/leg-duplicates', include_docs=True,
                        eager=True, key=[chamber, district, full_name])

    @classmethod
    def for_district_and_session(cls, db, chamber, district, session):
        """
        Returns the legislator(s) who served in the given chamber,
        district and session combination.
        """
        matches = cls.view(db, 'app/leg-with-sessions', include_docs=True,
                           eager=True)[[chamber, district, session]]

        if len(matches) == 0:
            return None

        return matches

    @classmethod
    def by_party_and_session(cls, db, party, session, chamber=None):
        """
        Returns the legislators who were members of the given party
        during the given session. Optionally filters by chamber as well.
        """
        if chamber:
            matches = cls.view(db, 'app/leg-by-party', include_docs=True,
                               eager=True, reduce=False)[[party,
                                                           session,
                                                           chamber]]
        else:
            matches = cls.view(db, 'app/leg-by-party', include_docs=True,
                               eager=True, reduce=False,
                               startkey=[party, session, None],
                               endkey=[party, session, "zzz"])

        if len(matches) == 0:
            return None

        return matches

    def votes(self, db, session):
        """
        Get all the votes made by this legislator in the given session.
        """

        def wrap(row):
            row.value.update({'bill': row.key[2]})
            return row.value

        key = [session, self.chamber, self.district]
        return db.view('app/leg-votes', startkey=[key, session, None],
                       endkey=[key, session, "z"], wrapper=wrap)


class Bill(FiftyStateDocument):
    type = TextField(default='bill')
    state = TextField()
    bill_id = TextField()
    chamber = TextField()
    session = TextField()
    title = TextField()

    sponsors = ListField(DictField(Schema.build(
        leg_id=TextField(),
        type=TextField(),
        name=TextField())))

    versions = ListField(DictField(Schema.build(
        url=TextField(),
        name=TextField())))

    votes = ListField(DictField(Schema.build(
        date=TextField(),
        threshold=TextField(),
        motion=TextField(),
        chamber=TextField(),
        location=TextField(),
        passed=BooleanField(),
        yes_count=IntegerField(),
        no_count=IntegerField(),
        other_count=IntegerField(),
        yes_votes=ListField(DictField(Schema.build(
            leg_id=TextField(),
            name=TextField()))),
        no_votes=ListField(DictField(Schema.build(
            leg_id=TextField(),
            name=TextField()))),
        other_votes=ListField(DictField(Schema.build(
            leg_id=TextField(),
            name=TextField()))))))
