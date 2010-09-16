================
Bill API Methods
================

.. contents::
   :depth: 2
   :local:


Bill Fields
===========

Both methods return bill objects consisting of the following fields:

``title``
    The title given to the bill by the state legislature.
``state``
    The 2-letter abbreviation of the state this bill is from (e.g. ``ny``).
``session``
    The session this bill was introduced in.
``chamber``
    The chamber this bill was introduced in (e.g. 'upper', 'lower')
``bill_id``
    The identifier given to this bill by the state legislature (e.g. 'AB6667')
``type``
    Bill type (see
    http://code.google.com/p/openstates/wiki/Categorization#Bills for
    details)
``alternate_titles``
    A list of alternate titles that this bill is/was known by, if available.
``updated_at``
    Timestamp representing when bill was last updated in our system.
``actions``
    A list of legislative actions performed on this bill. Each action will be an object with at least the following fields:

    * ``date``: The date/time the action was performed
    * ``actor``: The chamber, person, committee, etc. responsible for this action
    * ``action``: A textual description of the action performed
    * ``type``: A normalized type for the action, see http://code.google.com/p/openstates/wiki/Categorization#Bill_Actions for details.
``sponsors``
    A list of sponsors of this bill. Each sponsor will be an object with at least the following fields:

    * ``leg_id``: An Open State Project legislator ID (see :ref:``legislator lookup <leg-lookup>``)
    * ``full_name``: The name of the sponsor
    * ``type``: The type of sponsorship (state specific, examples include 'Primary Sponsor', 'Co-Sponsor')
``votes``
    A list of votes relating to this bill. Each vote will be an object with at least the following fields:

    * ``date``: The date/time the vote was taken
    * ``chamber``: The chamber that the vote was taken in
    * ``motion``: The motion being voted on
    * ``yes_count``, ``no_count``, ``other_count``: The number of 'yes', 'no', and other votes
    * ``yes_votes``, ``no_votes``, ``other_votes``: The legislators voting 'yes', 'no', and other
    * ``passed``: Whether or not the vote passed
    * ``type``: The normalized type for the vote. See http://code.google.com/p/openstates/wiki/Categorization#Vote_Types for details.
``versions``
    A list of versions of the text of this bill. Each version will be an object with at least the following fields:

    * ``url``: The URL for an official source of this version of the bill text
    * ``name``: A name for this version of the bill text
``documents``
    A list of documents related to this bill. Each document will be an object with at least the following fields:

    * ``url``: The URL for an official source of this document
    * ``name``: A name for this document (eg. 'Fiscal Statement', 'Education Committee Report')
``sources``
    List of sources that this data was collected from.

    * ``url``: URL of the source
    * ``retrieved``: time at which the source was last retrieved

.. note::
    ``actions``, ``sponsors``, ``votes``, ``versions``, ``documents``,
    ``alternate_title`` and ``sources`` are not returned via the search API.

.. note::
    Keep in mind that these documented fields may be a subset of the fields provided for a given state. (See :ref:`extrafields`)


Bill Search
===========

Search bills, either by keyword or by properties such as updated date or session.

Parameters
^^^^^^^^^^

When searching either a keyword (``q``) parameter is required or a ``state`` and ``session``.
All other parameters are optional and can be combined as needed.

``q``
    the keyword string to lookup
``state``
    filter results by given state (two-letter abbreviation)
``search_window``
    a string representing what time period to search across. Pass 'session'
    to search bills from the state's current or most recent legislative session,
    'term' to search the current or most recent term, 'all' to search as far back
    as the Open State Project has data for, or supply 'session:SESSION_NAME' or
    'term:TERM_NAME' (e.g. 'session:2009' or 'term:2009-2010') to search a
    specific session or term.
``chamber``
    filter results by given chamber ('upper' or 'lower')
``updated_since``
    only return bills that have been updated since a given date, YYYY-MM-DD format

URL Format
^^^^^^^^^^

:samp:`http://openstates.sunlightlabs.com/api/v1/bills/?{SEARCH-PARAMS}&apikey={YOUR_API_KEY}`

Example
^^^^^^^

http://openstates.sunlightlabs.com/api/v1/bills/?q=agriculture&state=vt&chamber=upper&apikey=YOUR_API_KEY

::

    [
        {
            "title": "AN ACT RELATING TO AGRICULTURAL FUNDING EDUCATION AND OUTREACH",
            "created_at": "2010-07-09 16:16:10",
            "updated_at": "2010-08-16 18:10:17",
            "chamber": "upper",
            "state": "vt",
            "session": "2009-2010",
            "type": [ "bill" ],
            "bill_id": "S.0132"
        },
        {
            "title": "AN ACT RELATING TO THE VERMONT AGRICULTURAL ADVISORY BOARD",
            "created_at": "2010-07-09 16:16:13",
            "updated_at": "2010-08-16 18:10:17",
            "chamber": "upper",
            "state": "vt",
            "session": "2009-2010",
            "type": [ "bill" ],
            "bill_id": "S.0208"
        },
        {
            "title": "AN ACT RELATING TO PUBLIC HEALTH AND PREVENTIVE HEALTH SERVICES FOR AGRICULTURAL AND FOOD SERVICE WORKERS",
            "created_at": "2010-07-09 16:16:09",
            "updated_at": "2010-08-16 18:10:17",
            "chamber": "upper",
            "state": "vt",
            "session": "2009-2010",
            "type": [ "bill" ],
            "bill_id": "S.0116"
        },
        {
            "title": "AN ACT RELATING TO THE USE OF TRANSFER OF DEVELOPMENT RIGHTS FOR OFF-SITE MITIGATION OF PRIMARY AGRICULTURAL SOILS",
            "created_at": "2010-07-09 16:16:14",
            "updated_at": "2010-08-16 18:10:17",
            "chamber": "upper",
            "state": "vt",
            "session": "2009-2010",
            "type": [ "bill" ],
            "bill_id": "S.0233"
        },
        {
            "title": "AN ACT RELATING TO AGRICULTURAL DEVELOPMENT, INCLUDING AGENCY POSITIONS AND CREATION OF DEVELOPMENT BOARD; ESTABLISHMENT OF LIVESTOCK CARE STANDARDS; OPERATION OF COMMERCIAL SLAUGHTER FACILITIES; ANIMAL RESCUE ORGANIZATIONS; AND HEALTH CERTIFICATES FOR IMPORTATION OF CERTAIN ANIMALS",
            "created_at": "2010-07-09 16:16:18",
            "updated_at": "2010-08-16 18:10:18",
            "chamber": "upper",
            "state": "vt",
            "session": "2009-2010",
            "type": [ "bill" ],
            "bill_id": "S.0295"
        }
    ]

Bill Lookup
===========

This endpoint exists to get all information about a bill given its state/session/chamber and bill id.

URL Format
^^^^^^^^^^

:samp:`http://openstates.sunlightlabs.com/api/v1/bills/{STATE-ABBREV}/{SESSION}/{BILL-ID}h?apikey={YOUR_API_KEY}`

alternatively, if BILL-ID is ambiguous, chamber may be prepended as part of the path:

:samp:`http://openstates.sunlightlabs.com/api/v1/bills/{STATE-ABBREV}/{SESSION}/{CHAMBER}/{BILL-ID}h?apikey={YOUR_API_KEY}`

Example
^^^^^^^

http://openstates.sunlightlabs.com/api/v1/bills/ca/20092010/AB667/?apikey=YOUR_API_KEY

::

   {
       "+short_title": "Topical flouride application.",
       "votes": [
           {
               "other_count": 0,
               "+threshold": "1/2",
               "other_votes": [],
               "yes_count": 7,
               "committee": "Local Government",
               "yes_votes": [
                   {
                       "leg_id": "CAL000086",
                       "name": "Arambula"
                   },
                   {
                       "leg_id": "CAL000066",
                       "name": "Caballero"
                   },
                   {
                       "leg_id": "CAL000090",
                       "name": "Davis"
                   },
                   {
                       "leg_id": "CAL000122",
                       "name": "Duvall"
                   },
                   {
                       "leg_id": "CAL000065",
                       "name": "Knight"
                   },
                   {
                       "leg_id": "CAL000100",
                       "name": "Krekorian"
                   },
                   {
                       "leg_id": "CAL000058",
                       "name": "Skinner"
                   }
               ],
               "motion": "Do pass, to Consent Calendar.",
               "chamber": "lower",
               "sources": [],
               "passed": true,
               "date": "2009-05-13 00:00:00",
               "type": "other",
               "no_count": 0,
               "no_votes": []
           },
           ...
       ],
       "documents": [],
       "title": "An act to amend Section 104830 of, and to add Section 104762 to, the Health and Safety Code, relating to oral health.",
       "+subjects": [
           "Topical flouride application."
       ],
       "versions": [
           {
               "+short_title": "Topical fluoride application.",
               "name": "20090AB66795CHP",
               "+type": [
                   "bill",
                   "fiscal committee"
               ],
               "url": "",
               "+title": "An act to amend Section 1750.1 of the Business and Professions Code, and to amend Section 104830 of, and to add Section 104762 to, the Health and Safety Code, relating to oral health.",
               "+subject": [
                   "Topical fluoride application."
               ],
               "+date": 1249516800.0
           },
           ...
       ],
       "updated_at": "2010-08-31 14:59:45",
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
           ...
       ],
       "sponsors": [
           {
               "chamber": "lower",
               "leg_id": "CAL000044",
               "type": "LEAD_AUTHOR",
               "name": "Block"
           }
       ],
       "sources": [],
       "state": "ca",
       "session": "20092010",
       "chamber": "lower",
       "type": [
           "bill",
           "fiscal committee"
       ],
       "created_at": "2010-07-09 17:28:10",
       "bill_id": "AB667"
   }

