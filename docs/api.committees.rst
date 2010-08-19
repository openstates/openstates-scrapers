=====================
Committee API Methods
=====================

.. contents::
   :depth: 2
   :local:


Committee Fields
================

Committee methods return objects with the following fields:

``committee``
    Name of committee.
``subcommittee``
    Name of subcommittee (null if record describes a top level committee).
``chamber``
    Associated chamber (upper or lower).
``state``
    State abbreviation (eg. ny).
``updated_at``
    Timestamp representing when bill was last updated in our system.
``members``
    Listing of all committee members.

    ``legislator``
        Name of legislator (as captured from source).
    ``role``
        Role of this member on the committee (usually 'member' but may indicate
        charimanship or other special status)
    ``leg_id``
        Legislator's Open State Project ID

.. note::
   ``members`` are not included in the committee search API results

.. note::
    Keep in mind that these documented fields may be a subset of the fields provided for a given state. (See :ref:`extrafields`)


Committee Lookup
================

Get all information about a committee given its Open State Project id.

URL Format
^^^^^^^^^^

:samp:`http://openstates.sunlightlabs.com/api/v1/committee/{COMMITTEE-ID}/?apikey={YOUR_API_KEY}`

Example
^^^^^^^

http://openstates.sunlightlabs.com/api/v1/committee/MDC000065/?apikey=YOUR_API_KEY

::

    {
        "committee": "HOUSE FACILITIES COMMITTEE",
        "sources": [
            {
                "url": "http://www.msa.md.gov/msa/mdmanual/06hse/html/com/sfacil.html",
                "retrieved": "2010-08-12 23:24:54"
            }
        ],
        "updated_at": "2010-08-12 23:25:18",
        "chamber": "lower",
        "state": "md",
        "subcommittee": null,
        "members": [
            {
                "leg_id": "MDL000123",
                "role": "member",
                "legislator": "Carolyn J. Krysiak"
            },
            {
                "leg_id": "MDL000120",
                "role": "member",
                "legislator": "Ruth M. Kirk"
            },
            {
                "leg_id": "MDL000129",
                "role": "member",
                "legislator": "Mary Ann Love"
            },
            {
                "leg_id": "MDL000144",
                "role": "member",
                "legislator": "LeRoy E. Myers, Jr."
            },
            {
                "leg_id": "MDL000152",
                "role": "member",
                "legislator": "Shane E. Pendergrass"
            }
        ]
    }


Committee Search
================

Search committees by properties such as state or chamber.

Parameters
^^^^^^^^^^

``committee``
    name of a committee
``subcommittee``
    name of a subcommittee
``chamber``
    filter results by given chamber (upper or lower)
``state``
    return committees for a given state (eg. ny)

URL Format
^^^^^^^^^^

:samp:`http://openstates.sunlightlabs.com/api/v1/committees/?{SEARCH-PARAMS}&apikey={YOUR_API_KEY}`

Example
^^^^^^^

http://openstates.sunlightlabs.com/api/v1/committees/?state=md&chamber=upper&apikey=YOUR_API_KEY

::

    [
        {
            "chamber": "upper",
            "state": "md",
            "updated_at": "2010-08-12 23:25:15",
            "committee": "EDUCATION, HEALTH & ENVIRONMENTAL AFFAIRS COMMITTEE",
            "subcommittee": "ALCOHOLIC BEVERAGES SUBCOMMITTEE"
        },
        {
            "chamber": "upper",
            "state": "md",
            "updated_at": "2010-08-12 23:25:16",
            "committee": "SPECIAL COMMITTEE ON SUBSTANCE ABUSE",
            "subcommittee": null
        },
        {
            "chamber": "upper",
            "state": "md",
            "updated_at": "2010-08-12 23:25:15",
            "committee": "RULES COMMITTEE",
            "subcommittee": null
        },
        {
            "chamber": "upper",
            "state": "md",
            "updated_at": "2010-08-12 23:25:15",
            "committee": "JUDICIAL PROCEEDINGS COMMITTEE",
            "subcommittee": null
        },
        {
            "chamber": "upper",
            "state": "md",
            "updated_at": "2010-08-12 23:25:15",
            "committee": "BUDGET & TAXATION COMMITTEE",
            "subcommittee": null
        },
        {
            "chamber": "upper",
            "state": "md",
            "updated_at": "2010-08-12 23:25:15",
            "committee": "BUDGET & TAXATION COMMITTEE",
            "subcommittee": "CAPITAL BUDGET SUBCOMMITTEE"
        },
        {
            "chamber": "upper",
            "state": "md",
            "updated_at": "2010-08-12 23:25:15",
            "committee": "BUDGET & TAXATION COMMITTEE",
            "subcommittee": "HEALTH, EDUCATION & HUMAN RESOURCES SUBCOMMITTEE"
        },
        {
            "chamber": "upper",
            "state": "md",
            "updated_at": "2010-08-12 23:25:15",
            "committee": "BUDGET & TAXATION COMMITTEE",
            "subcommittee": "PENSIONS SUBCOMMITTEE"
        },
        {
            "chamber": "upper",
            "state": "md",
            "updated_at": "2010-08-12 23:25:15",
            "committee": "BUDGET & TAXATION COMMITTEE",
            "subcommittee": "PUBLIC SAFETY, TRANSPORTATION & ENVIRONMENT SUBCOMMITTEE"
        },
        {
            "chamber": "upper",
            "state": "md",
            "updated_at": "2010-08-12 23:25:15",
            "committee": "EDUCATION, HEALTH & ENVIRONMENTAL AFFAIRS COMMITTEE",
            "subcommittee": null
        },
        {
            "chamber": "upper",
            "state": "md",
            "updated_at": "2010-08-12 23:25:15",
            "committee": "EDUCATION, HEALTH & ENVIRONMENTAL AFFAIRS COMMITTEE",
            "subcommittee": "BASE REALIGNMENT & CLOSURE (BRAC) SUBCOMMITTEE"
        },
        {
            "chamber": "upper",
            "state": "md",
            "updated_at": "2010-08-12 23:25:15",
            "committee": "EDUCATION, HEALTH & ENVIRONMENTAL AFFAIRS COMMITTEE",
            "subcommittee": "EDUCATION SUBCOMMITTEE"
        },
        {
            "chamber": "upper",
            "state": "md",
            "updated_at": "2010-08-12 23:25:15",
            "committee": "EDUCATION, HEALTH & ENVIRONMENTAL AFFAIRS COMMITTEE",
            "subcommittee": "ENVIRONMENT SUBCOMMITTEE"
        },
        {
            "chamber": "upper",
            "state": "md",
            "updated_at": "2010-08-12 23:25:15",
            "committee": "EDUCATION, HEALTH & ENVIRONMENTAL AFFAIRS COMMITTEE",
            "subcommittee": "ETHICS & ELECTION LAW SUBCOMMITTEE"
        },
        {
            "chamber": "upper",
            "state": "md",
            "updated_at": "2010-08-12 23:25:15",
            "committee": "EDUCATION, HEALTH & ENVIRONMENTAL AFFAIRS COMMITTEE",
            "subcommittee": "HEALTH SUBCOMMITTEE"
        },
        {
            "chamber": "upper",
            "state": "md",
            "updated_at": "2010-08-12 23:25:15",
            "committee": "FINANCE COMMITTEE",
            "subcommittee": null
        },
        {
            "chamber": "upper",
            "state": "md",
            "updated_at": "2010-08-12 23:25:15",
            "committee": "FINANCE COMMITTEE",
            "subcommittee": "HEALTH SUBCOMMITTEE"
        },
        {
            "chamber": "upper",
            "state": "md",
            "updated_at": "2010-08-12 23:25:15",
            "committee": "FINANCE COMMITTEE",
            "subcommittee": "TRANSPORTATION SUBCOMMITTEE"
        },
        {
            "chamber": "upper",
            "state": "md",
            "updated_at": "2010-08-12 23:25:15",
            "committee": "EXECUTIVE NOMINATIONS COMMITTEE",
            "subcommittee": null
        }
    ]

