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
  * ``suffixes``
  * ``photo_url``
  * ``active`` Whether this legislator is currently serving
  * ``state``, ``chamber``, ``district``, ``party`` (only present if the legislator is
    currently serving)
  * ``roles``: A list of objects representing roles this legislator
    has held. Each role will contain at least the ``type`` and
    ``term`` roles:

    * ``type`` the type of role - e.g. "member", "committee member",
      "Lt. Governor"
    * ``term`` the term the role was held during
    * ``chamber``
    * ``district``
    * ``party``
    * ``committee``
    * ``term``
  * ``sources``
    List of sources that this data was collected from.

      * ``url``: URL of the source
      * ``retrieved``: time at which the source was last retrieved

.. note::
    ``sources`` and ``roles`` are not included in the legislator search response.

.. note::
    Keep in mind that these documented fields may be a subset of the fields provided for a given state. (See :ref:`extrafields`)


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
``active``
    Restrict the search to currently-active legislators (the default) - 'true' or 'false'.
``term``
    Filter by legislators who served during a certain term.
``district``
    Filter by legislative district.
``party``
    Filter by the legislator's party, e.g. 'Democratic' or 'Republican'.

URL format
----------

:samp:`http://openstates.sunlightlabs.com/api/v1/legislators/?{SEARCH-PARAMS}&apikey={YOUR_API_KEY}`

Example
-------

http://openstates.sunlightlabs.com/api/v1/legislators/?state=ca&party=democratic&first_name=Bob&active=true&apikey=YOUR_API_KEY

::

    [
        {
            "first_name": "Bob",
            "last_name": "Blumenfield",
            "middle_name": "",
            "district": "40",
            "created_at": "2010-07-09 17:19:48",
            "updated_at": "2010-08-30 21:41:37",
            "chamber": "lower",
            "state": "ca",
            "nimsp_candidate_id": null,
            "votesmart_id": "104387",
            "full_name": "Blumenfield, Bob",
            "leg_id": "CAL000088",
            "party": "Democratic",
            "photo_url": "http://www.assembly.ca.gov/images/members/40.jpg",
            "active": true,
            "id": "CAL000088",
            "suffixes": ""
        }
    ]


Legislator Lookup
=================

Lookup all available data for a legislator given their Open State Project ``leg_id``.

URL Format
----------

:samp:`http://openstates.sunlightlabs.com/api/v1/legislators/{LEG_ID}/?apikey={YOUR_API_KEY}`

Example
-------

http://openstates.sunlightlabs.com/api/v1/legislators/MDL000210/?apikey=YOUR_API_KEY

::

    {
        "first_name": "Verna L.",
        "last_name": "Jones",
        "middle_name": "",
        "roles": [
            {
                "term": "2007-2010",
                "end_date": null,
                "district": "44",
                "chamber": "upper",
                "state": "md",
                "party": "Democratic",
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
        "district": "44",
        "state": "md",
        "created_at": "2010-08-27 22:54:37",
        "updated_at": "2010-08-31 22:45:34",
        "chamber": "upper",
        "leg_id": "MDL000210",
        "sources": [
            {
                "url": "http://www.msa.md.gov/msa/mdmanual/05sen/html/msa02779.html",
                "retrieved": "2010-08-31 21:15:55"
            }
        ],
        "votesmart_id": "19142",
        "full_name": "Verna L. Jones",
        "active": true,
        "party": "Democratic",
        "id": "MDL000210",
        "suffixes": ""
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

:samp:`http://openstates.sunlightlabs.com/api/v1/legislators/geo/?lat={LATITUDE}&long={LONGITUDE}&apikey={YOUR_API_KEY}`

Example
-------

http://openstates.sunlightlabs.com/api/v1/legislators/geo/?lat=-78.76648&long=35.81336&apikey=YOUR_API_KEY

::

    [
        {
            "created_at": "2010-08-03 17:14:48",
            "first_name": "Jennifer",
            "last_name": "Weiss",
            "middle_name": "",
            "suffix": "",
            "district": "35",
            "chamber": "lower",
            "roles": [
                {
                    "term": "2009-2010",
                    "end_date": null,
                    "district": "35",
                    "chamber": "lower",
                    "state": "nc",
                    "party": "Democratic",
                    "type": "member",
                    "start_date": null
                }
            ],
            "updated_at": "2010-09-01 01:11:12",
            "sources": [
                {
                    "url": "http://www.ncga.state.nc.us/gascripts/members/memberList.pl?sChamber=House",
                    "retrieved": "2010-08-31 23:53:37"
                }
            ],
            "state": "nc",
            "nimsp_candidate_id": 99623,
            "votesmart_id": "40966",
            "full_name": "Jennifer Weiss",
            "leg_id": "NCL000172",
            "party": "Democratic",
            "active": true,
            "id": "NCL000172",
            "suffixes": ""
        },
        {
            "created_at": "2010-08-03 17:14:46",
            "first_name": "Josh",
            "last_name": "Stein",
            "middle_name": "",
            "suffix": "",
            "district": "16",
            "chamber": "upper",
            "roles": [
                {
                    "term": "2009-2010",
                    "end_date": null,
                    "district": "16",
                    "chamber": "upper",
                    "state": "nc",
                    "party": "Democratic",
                    "type": "member",
                    "start_date": null
                },
                {
                    "term": "2009-2010",
                    "committee_id": "NCC000002",
                    "chamber": "upper",
                    "state": "nc",
                    "subcommittee": null,
                    "committee": "Appropriations on Department of Transportation",
                    "type": "committee member"
                },
                {
                    "term": "2009-2010",
                    "committee_id": "NCC000008",
                    "chamber": "upper",
                    "state": "nc",
                    "subcommittee": null,
                    "committee": "Appropriations/Base Budget",
                    "type": "committee member"
                },
                {
                    "term": "2009-2010",
                    "committee_id": "NCC000009",
                    "chamber": "upper",
                    "state": "nc",
                    "subcommittee": null,
                    "committee": "Commerce",
                    "type": "committee member"
                },
                {
                    "term": "2009-2010",
                    "committee_id": "NCC000010",
                    "chamber": "upper",
                    "state": "nc",
                    "subcommittee": null,
                    "committee": "Education/Higher Education",
                    "type": "committee member"
                },
                {
                    "term": "2009-2010",
                    "committee_id": "NCC000011",
                    "chamber": "upper",
                    "state": "nc",
                    "subcommittee": null,
                    "committee": "Finance",
                    "type": "committee member"
                },
                {
                    "term": "2009-2010",
                    "committee_id": "NCC000012",
                    "chamber": "upper",
                    "state": "nc",
                    "subcommittee": null,
                    "committee": "Health Care",
                    "type": "committee member"
                },
                {
                    "term": "2009-2010",
                    "committee_id": "NCC000014",
                    "chamber": "upper",
                    "state": "nc",
                    "subcommittee": null,
                    "committee": "Judiciary I",
                    "type": "committee member"
                },
                {
                    "term": "2009-2010",
                    "committee_id": "NCC000022",
                    "chamber": "upper",
                    "state": "nc",
                    "subcommittee": null,
                    "committee": "Select Committee on Economic Recovery",
                    "type": "committee member"
                },
                {
                    "term": "2009-2010",
                    "committee_id": "NCC000024",
                    "chamber": "upper",
                    "state": "nc",
                    "subcommittee": null,
                    "committee": "Select Committee on Energy, Science and Technology",
                    "type": "committee member"
                }
            ],
            "updated_at": "2010-09-01 01:11:35",
            "sources": [
                {
                    "url": "http://www.ncga.state.nc.us/gascripts/members/memberList.pl?sChamber=Senate",
                    "retrieved": "2010-08-31 23:53:35"
                }
            ],
            "state": "nc",
            "nimsp_candidate_id": 99584,
            "votesmart_id": "102971",
            "full_name": "Josh Stein",
            "leg_id": "NCL000047",
            "party": "Democratic",
            "active": true,
            "id": "NCL000047",
            "suffixes": ""
        }
    ]
