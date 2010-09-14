=====================
Committee API Methods
=====================

.. contents::
   :depth: 2
   :local:


Committee Fields
================

Committee methods return objects with the following fields:

``id``
    Open State Project Committee ID.
``chamber``
    Associated chamber (upper or lower).
``state``
    State abbreviation (eg. ny).
``committee``
    Name of committee.
``subcommittee``
    Name of subcommittee (null if record describes a top level
    committee).
``parent_id``
    For subcommittees, the committee ID of its parent. ``null`` otherwise.
``members``
    Listing of all committee members.

    ``legislator``
        Name of legislator (as captured from source).
    ``role``
        Role of this member on the committee (usually 'member' but may indicate
        charimanship or other special status)
    ``leg_id``
        Legislator's Open State Project ID
``sources``
    List of sources that this data was collected from.

    ``url``
        URL of the source
    ``retrieved``
        time at which the source was last retrieved

.. note::
   ``members`` and ``sources`` are not included in the committee search API results

.. note::
    Keep in mind that these documented fields may be a subset of the fields provided for a given state. (See :ref:`extrafields`)


Committee Lookup
================

Get all information about a committee given its Open State Project id.

URL Format
^^^^^^^^^^

:samp:`http://openstates.sunlightlabs.com/api/v1/committees/{COMMITTEE-ID}/?apikey={YOUR_API_KEY}`

Example
^^^^^^^

http://openstates.sunlightlabs.com/api/v1/committees/MDC000065/?apikey=YOUR_API_KEY

::

    {
        "members": [
            {
                "leg_id": "MDL000313",
                "role": "member",
                "legislator": "Carolyn J. Krysiak"
            },
            {
                "leg_id": "MDL000310",
                "role": "member",
                "legislator": "Ruth M. Kirk"
            },
            {
                "leg_id": "MDL000319",
                "role": "member",
                "legislator": "Mary Ann Love"
            },
            {
                "leg_id": "MDL000334",
                "role": "member",
                "legislator": "LeRoy E. Myers, Jr."
            },
            {
                "leg_id": "MDL000342",
                "role": "member",
                "legislator": "Shane E. Pendergrass"
            }
        ],
        "sources": [
            {
                "url": "http://www.msa.md.gov/msa/mdmanual/06hse/html/com/sfacil.html",
                "retrieved": "2010-08-31 16:52:52"
            }
        ],
        "updated_at": "2010-08-31 16:53:19",
        "chamber": "lower",
        "state": "md",
        "subcommittee": null,
        "committee": "HOUSE FACILITIES COMMITTEE",
        "id": "MDC000065"
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
            "updated_at": "2010-08-31 16:53:16",
            "chamber": "upper",
            "state": "md",
            "subcommittee": "ALCOHOLIC BEVERAGES SUBCOMMITTEE",
            "committee": "EDUCATION, HEALTH & ENVIRONMENTAL AFFAIRS COMMITTEE",
            "id": "MDC000009"
        },
        {
            "updated_at": "2010-08-31 16:53:16",
            "chamber": "upper",
            "state": "md",
            "subcommittee": null,
            "committee": "SPECIAL COMMITTEE ON SUBSTANCE ABUSE",
            "id": "MDC000019"
        },
        {
            "updated_at": "2010-08-31 16:53:16",
            "chamber": "upper",
            "state": "md",
            "subcommittee": null,
            "committee": "RULES COMMITTEE",
            "id": "MDC000001"
        },
        {
            "updated_at": "2010-08-31 16:53:16",
            "chamber": "upper",
            "state": "md",
            "subcommittee": null,
            "committee": "JUDICIAL PROCEEDINGS COMMITTEE",
            "id": "MDC000002"
        },
        {
            "updated_at": "2010-08-31 16:53:16",
            "chamber": "upper",
            "state": "md",
            "subcommittee": null,
            "committee": "BUDGET & TAXATION COMMITTEE",
            "id": "MDC000003"
        },
        {
            "updated_at": "2010-08-31 16:53:16",
            "chamber": "upper",
            "state": "md",
            "subcommittee": "CAPITAL BUDGET SUBCOMMITTEE",
            "committee": "BUDGET & TAXATION COMMITTEE",
            "id": "MDC000004"
        },
        {
            "updated_at": "2010-08-31 16:53:16",
            "chamber": "upper",
            "state": "md",
            "subcommittee": "HEALTH, EDUCATION & HUMAN RESOURCES SUBCOMMITTEE",
            "committee": "BUDGET & TAXATION COMMITTEE",
            "id": "MDC000005"
        },
        {
            "updated_at": "2010-08-31 16:53:16",
            "chamber": "upper",
            "state": "md",
            "subcommittee": "PENSIONS SUBCOMMITTEE",
            "committee": "BUDGET & TAXATION COMMITTEE",
            "id": "MDC000006"
        },
        {
            "updated_at": "2010-08-31 16:53:16",
            "chamber": "upper",
            "state": "md",
            "subcommittee": "PUBLIC SAFETY, TRANSPORTATION & ENVIRONMENT SUBCOMMITTEE",
            "committee": "BUDGET & TAXATION COMMITTEE",
            "id": "MDC000007"
        },
        {
            "updated_at": "2010-08-31 16:53:16",
            "chamber": "upper",
            "state": "md",
            "subcommittee": null,
            "committee": "EDUCATION, HEALTH & ENVIRONMENTAL AFFAIRS COMMITTEE",
            "id": "MDC000008"
        },
        {
            "updated_at": "2010-08-31 16:53:16",
            "chamber": "upper",
            "state": "md",
            "subcommittee": "BASE REALIGNMENT & CLOSURE (BRAC) SUBCOMMITTEE",
            "committee": "EDUCATION, HEALTH & ENVIRONMENTAL AFFAIRS COMMITTEE",
            "id": "MDC000010"
        },
        {
            "updated_at": "2010-08-31 16:53:16",
            "chamber": "upper",
            "state": "md",
            "subcommittee": "EDUCATION SUBCOMMITTEE",
            "committee": "EDUCATION, HEALTH & ENVIRONMENTAL AFFAIRS COMMITTEE",
            "id": "MDC000011"
        },
        {
            "updated_at": "2010-08-31 16:53:16",
            "chamber": "upper",
            "state": "md",
            "subcommittee": "ENVIRONMENT SUBCOMMITTEE",
            "committee": "EDUCATION, HEALTH & ENVIRONMENTAL AFFAIRS COMMITTEE",
            "id": "MDC000012"
        },
        {
            "updated_at": "2010-08-31 16:53:16",
            "chamber": "upper",
            "state": "md",
            "subcommittee": "ETHICS & ELECTION LAW SUBCOMMITTEE",
            "committee": "EDUCATION, HEALTH & ENVIRONMENTAL AFFAIRS COMMITTEE",
            "id": "MDC000013"
        },
        {
            "updated_at": "2010-08-31 16:53:16",
            "chamber": "upper",
            "state": "md",
            "subcommittee": "HEALTH SUBCOMMITTEE",
            "committee": "EDUCATION, HEALTH & ENVIRONMENTAL AFFAIRS COMMITTEE",
            "id": "MDC000014"
        },
        {
            "updated_at": "2010-08-31 16:53:16",
            "chamber": "upper",
            "state": "md",
            "subcommittee": null,
            "committee": "FINANCE COMMITTEE",
            "id": "MDC000015"
        },
        {
            "updated_at": "2010-08-31 16:53:16",
            "chamber": "upper",
            "state": "md",
            "subcommittee": "HEALTH SUBCOMMITTEE",
            "committee": "FINANCE COMMITTEE",
            "id": "MDC000016"
        },
        {
            "updated_at": "2010-08-31 16:53:16",
            "chamber": "upper",
            "state": "md",
            "subcommittee": "TRANSPORTATION SUBCOMMITTEE",
            "committee": "FINANCE COMMITTEE",
            "id": "MDC000017"
        },
        {
            "updated_at": "2010-08-31 16:53:16",
            "chamber": "upper",
            "state": "md",
            "subcommittee": null,
            "committee": "EXECUTIVE NOMINATIONS COMMITTEE",
            "id": "MDC000018"
        }
    ]
