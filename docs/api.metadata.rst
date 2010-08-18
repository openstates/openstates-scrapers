==========================
State Metadata API Methods
==========================

State Metadata
==============

Grab metadata about a certain state.

Metadata Fields
---------------

``name``
    The name of the state
``abbreviation``
    The two-letter abbreviation of the state
``legislature_name``
    The name of the state legislature
``upper_chamber_name``
    The name of the 'upper' chamber of the state legislature (if applicable)
``lower_chamber_name``
    The name of the 'lower' chamber of the state legislature (if applicable)
``upper_chamber_term``
    The length, in years, of a term for members of the 'upper' chamber (if applicable)
``lower_chamber_term``
    The length, in years, of a term for members of the 'lower' chamber (if applicable)
``upper_chamber_title``
    The title used to refer to members of the 'upper' chamber (if applicable)
``lower_chamber_title``
    The title used to refer to members of the 'lower' chamber (if applicable)
``sessions``
    A list of sessions that we have data available for. Each session will be an object with the following fields:
    * ``start_year``: The year in which this session began.
    * ``end_year``: The year in which this session ended.
    * ``name``: The name of this session.

URL format
----------

http://openstates.sunlightlabs.com/api/v1/metadata/:STATE-ABBREV:/?apikey=YOUR_API_KEY


Example
-------

http://openstates.sunlightlabs.com/api/v1/metadta/ca/?apikey=YOUR_API_KEY

::

    {
        "lower_chamber_title": "Assemblymember",
        "lower_chamber_name": "Assembly",
        "upper_chamber_title": "Senator",
        "terms": [
            {
                "end_year": 2010,
                "start_year": 2009,
                "name": "20092010",
                "sessions": [
                    "20092010",
                    "20092010 Special Session 1",
                    "20092010 Special Session 2",
                    "20092010 Special Session 3",
                    "20092010 Special Session 4",
                    "20092010 Special Session 5",
                    "20092010 Special Session 6",
                    "20092010 Special Session 7",
                    "20092010 Special Session 8"
                ]
            }
        ],
        "name": "California",
        "upper_chamber_term": 4,
        "abbreviation": "ca",
        "upper_chamber_name": "Senate",
        "legislature_name": "California State Legislature",
        "lower_chamber_term": 3
    }

