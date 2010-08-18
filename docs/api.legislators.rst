======================
Legislator API Methods
======================

.. contents::
    :depth: 2
    :local:

Legislator Fields
=================

All legislator methods return Legislator objects consisting of the following fields:

  * ``leg_id``: A permanent, unique identifier for this legislator within the Fifty State Project system.
  * ``full_name``
  * ``first_name``
  * ``last_name``
  * ``middle_name``
  * ``suffix``
  * ``party``
  * ``roles``: A list of objects representing roles this legislator has served in. Each object will contain at least the following fields:

    * ``state``
    * ``session``
    * ``chamber``
    * ``district``

.. note::
    Roles are not included in the response in legislator search.

Legislator Search
=================

Searches for legislators matching certain criteria.

Parameters
----------

``state``
    Filter by state served in (two-letter state abbreviation)
``first_name``, ``last_name``
    Filter by name
``chamber``
    Filter by legislator's chamber, i.e. 'upper' or 'lower'.
``term``
    Filter by legislators who served during a certain term.
``district``
    Filter by legislative district.
``party``
    Filter by the legislator's party, e.g. 'Democrat' or 'Republican'.

URL format
----------

http://openstates.sunlightlabs.com/api/v1/legislators/?:SEARCH-PARAMS:&apikey=YOUR_API_KEY

Example
-------

http://openstates.sunlightlabs.com/api/v1/legislators/?state=ca&party=democrat&first_name=Bob&apikey=YOUR_API_KEY

::

    [
        {
            "first_name": "Bob",
            "last_name": "Blumenfield",
            "middle_name": "",
            "created_at": "2010-07-09 17:19:48",
            "updated_at": "2010-08-10 19:57:02",
            "state": "ca",
            "nimsp_candidate_id": null,
            "votesmart_id": "104387",
            "full_name": "Blumenfield, Bob",
            "leg_id": "CAL000088",
            "id": "CAL000088",
            "suffixes": ""
        }
    ]


Legislator Lookup
=================

Lookup all available data for a legislator given their Open State Project ``leg_id``.

URL Format
----------

http://openstates.sunlightlabs.com/api/v1/legislators/:LEG_ID:/?apikey=YOUR_API_KEY

Example
-------

http://openstates.sunlightlabs.com/api/v1/legislators/MDL000021/?apikey=YOUR_API_KEY

::

    {
        "first_name": "Verna L.",
        "last_name": "Jones",
        "middle_name": "",
        "suffix": null,
        "roles": [
            {
                "term": "2007-2010",
                "end_date": null,
                "district": "44",
                "chamber": "upper",
                "state": "md",
                "party": "D",
                "type": "member",
                "start_date": null
            },
            {
                "term": "2007-2010",
                "committee_id": "MDC000003",
                "chamber": "upper",
                "state": "md",
                "subcommittee": null,
                "committee": "BUDGET & TAXATION COMMITTEE",
                "type": "committee member"
            },
            {
                "term": "2007-2010",
                "committee_id": "MDC000007",
                "chamber": "upper",
                "state": "md",
                "subcommittee": "PUBLIC SAFETY, TRANSPORTATION & ENVIRONMENT SUBCOMMITTEE",
                "committee": "BUDGET & TAXATION COMMITTEE",
                "type": "committee member"
            },
            {
                "term": "2007-2010",
                "committee_id": "MDC000019",
                "chamber": "upper",
                "state": "md",
                "subcommittee": null,
                "committee": "SPECIAL COMMITTEE ON SUBSTANCE ABUSE",
                "type": "committee member"
            }
        ],
        "url": "http://www.msa.md.gov/msa/mdmanual/05sen/html/msa02779.html",
        "created_at": "2010-07-12 16:17:11",
        "updated_at": "2010-08-12 23:25:16",
        "sources": [],
        "state": "md",
        "nimsp_candidate_id": null,
        "votesmart_id": "19142",
        "full_name": "Verna L. Jones",
        "leg_id": "MDL000021",
        "id": "MDL000021"
    }


Geo Lookup
==========

Lookup all legislators that serve districts containing a given geographical point.

Parameters
----------

``lat``
    Latitude of point to use for district lookup
``long``
    Longitude of point to use for district lookup

URL Format
----------

http://openstates.sunlightlabs.com/api/v1/legislators/geo/?lat=:LATITUDE:&long=:LONGITUDE:&apikey=YOUR_API_KEY

Example
-------

http://openstates.sunlightlabs.com/api/v1/legislators/geo/?lat=-73.675451&long=42.73749&apikey=YOUR_API_KEY

::

    [
        {
            "first_name": "Roy",
            "last_name": "McDonald",
            "middle_name": "J.",
            "roles": [
                {
                    "end_date": null,
                    "district": "43",
                    "chamber": "upper",
                    "state": "ny",
                    "session": "2009-2010",
                    "party": "Conservative",
                    "type": "member",
                    "start_date": null
                }
            ],
            "created_at": "2010-06-17 14:33:34",
            "updated_at": "2010-06-17 14:33:34",
            "sources": [],
            "state": "ny",
            "nimsp_candidate_id": 111314,
            "votesmart_id": "44926",
            "full_name": "Roy J. McDonald",
            "leg_id": "NYL000034",
            "id": "NYL000034"
        },
        {
            "first_name": "Ronald",
            "last_name": "Canestrari",
            "middle_name": "J.",
            "roles": [
                {
                    "end_date": null,
                    "district": "106",
                    "chamber": "lower",
                    "state": "ny",
                    "session": "2009-2010",
                    "party": "Democratic",
                    "type": "member",
                    "start_date": null
                }
            ],
            "created_at": "2010-06-17 14:33:34",
            "updated_at": "2010-06-17 14:33:34",
            "sources": [],
            "state": "ny",
            "nimsp_candidate_id": 95987,
            "votesmart_id": "4286",
            "full_name": "Ronald J. Canestrari",
            "leg_id": "NYL000087",
            "id": "NYL000087"
        }
    ]
