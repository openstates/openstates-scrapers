====================================
Open State Project API: Bill Methods
====================================

There are three endpoints pertaining to bills:
    * single bill lookup
    * search
    * date-based lookup

All three methods return bill objects which have several fields in common:

Bill Fields
===========

``title``
    The title given to the bill by the state legislature
``state``
    The state this bill is from
``session``
    The session this bill was introduced in
``chamber``
    The chamber this bill was introduced in (e.g. 'upper', 'lower')
``bill_id``
    The identifier given to this bill by the state legislature (e.g. 'AB6667')
``actions``
    A list of legislative actions performed on this bill. Each action will be an object with at least the following fields:
    * ``date``: The date/time the action was performed
    * ``actor``: The chamber, person, committee, etc. responsible for this action
    * ``action``: A textual description of the action performed
``sponsors``
    A list of sponsors of this bill. Each sponsor will be an object with at least the following fields:

    * ``leg_id``: A Fifty State Project legislator ID (see :ref:``legislator lookup <leg-lookup>``)
    * ``full_name``: The name of the sponsor
    * ``type``: The type of sponsorship (state specific, examples include 'Primary Sponsor', 'Co-Sponsor')
``votes``
    A list of votes relating to this bill. Each vote will be an object with at least the following fields:
    * ``date``: The date/time the vote was taken
    * ``chamber``: The chamber that the vote was taken in
    * ``motion``: The motion being voted on
    * ``yes_count``, ``no_count``, ``other_count``: The number of 'yes', 'no', and other votes
    * ``passed``: Whether or not the vote passed
``versions``
    A list of versions of the text of this bill. Each version will be an object with at least the following fields:

    * ``url``: The URL for an official source of this version of the bill text
    * ``name``: A name for this version of the bill text

Single Bill Lookup
==================

This endpoint exists to get all information about a bill given its state/session/chamber and Open State Project id.

URL Format
^^^^^^^^^^

http://openstates.sunlightlabs.com/api/:STATE-ABBREV:/:SESSION:/:CHAMBER:/bills/:BILL-ID:/?apikey=YOUR_API_KEY

Example
^^^^^^^

http://openstates.sunlightlabs.com/api/ca/20092010/lower/bills/AB667/?apikey=YOUR_API_KEY

::

    {
        "votes": [
            {
                "other_count": 0, 
                "threshold": "1/2", 
                "passed": true, 
                "other_votes": [], 
                "yes_count": 7, 
                "yes_votes": [
                    {
                        "leg_id": "CAL000086", 
                        "name": "Arambula"
                    }, 
                    {
                        "leg_id": "CAL000066", 
                        "name": "Caballero"
                    }, 
                    ...
                ], 
                "motion": "Do pass, to Consent Calendar.", 
                "chamber": "lower", 
                "sources": [], 
                "committee": "Local Government", 
                "date": "2009-05-13 00:00:00", 
                "type": "other", 
                "no_count": 0, 
                "no_votes": []
            }, 
            ...
        ], 
        "documents": [], 
        "title": "An act to amend Section 104830 of, and to add Section 104762 to, the Health and Safety Code, relating to oral health.", 
        "created_at": "2010-07-09 17:28:10", 
        "versions": [
            {
                "name": "20090AB66795CHP", 
                "title": "An act to amend Section 1750.1 of the Business and Professions Code, and to amend Section 104830 of, and to add Section 104762 to, the Health and Safety Code, relating to oral health.", 
                "url": "", 
                "short_title": "Topical fluoride application.", 
                "date": 1249516800.0, 
                "type": [
                    "bill", 
                    "fiscal committee"
                ], 
                "subject": [
                    "Topical fluoride application."
                ]
            }, 
            ...
        ], 
        "updated_at": "2010-08-11 17:02:49", 
        "short_title": "Topical flouride application.", 
        "sponsors": [
            {
                "leg_id": "CAL000044", 
                "type": "LEAD_AUTHOR", 
                "name": "Block"
            }
        ], 
        "chamber": "lower", 
        "state": "ca", 
        "session": "20092010", 
        "sources": [], 
        "actions": [
            {
                "date": "2009-04-02 00:00:00", 
                "action": "From committee chair, with author's amendments:  Amend, and re-refer to Com. on  HEALTH. Read second time and amended.", 
                "type": [
                    "other"
                ], 
                "actor": "lower (E&E Engrossing)"
            }, 
            {
                "date": "2009-04-13 00:00:00", 
                "action": "Re-referred to Com. on  HEALTH.", 
                "type": [
                    "other"
                ], 
                "actor": "lower (Committee CX08)"
            }, 
        ], 
        "keywords": [ "code", "safeti", "amend", "section", "relat", "104830", 
            "add", "health", "104762", "act", "oral" ], 
        "type": [
            "bill", 
            "fiscal committee"
        ], 
        "subjects": [
            "Topical flouride application."
        ], 
        "bill_id": "AB667"
    }


Bill Search
-----------

Endpoint to search bills by keywords, optionally faceting on a number of fields.

Parameters
^^^^^^^^^^

``q`` (**required**)
    the keyword string to lookup
``state`` (*optional*)
    filter results by given state (two-letter abbreviation)
``session`` (*optional*)
    filter results by given session
``chamber`` (*optional*)
    filter results by given chamber ('upper' or 'lower')
``updated_since`` (*optional*)
    only return bills that have been updated since a given date, YYYY-MM-DD format

Returns a list of bills containing the same fields returned a simple lookup.

.. note::
    Will only return the first 20 matching bills. If no bills match, an empty list is returned.

URL Format
^^^^^^^^^^

http://openstates.sunlightlabs.com/api/bills/search/?:SEARCH-PARAMS:&apikey=YOUR_API_KEY

Example
^^^^^^^

http://openstates.sunlightlabs.com/api/bills/search/?q=agriculture&state=vt&apikey=YOUR_API_KEY


Latest Bills
------------

Get all bills updated since a certain time.

Parameters
^^^^^^^^^^

``updated_since``
    how far back to search, in YYYY-MM-DD format
``state``
    the state to search (two-letter abbreviation)

URL Format
^^^^^^^^^^
    http://openstates.sunlightlabs.com/api/bills/latest/?updated_since=:TIMESTAMP:&state=:STATE-ABBREV:&apikey=YOUR_API_KEY

Example
^^^^^^^
    http://openstates.sunlightlabs.com/api/bills/latest/?updated_since=2010-04-01&state=sd&apikey=YOUR_API_KEY

