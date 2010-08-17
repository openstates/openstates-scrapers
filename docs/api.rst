*****************
Open States API
*****************

Basic Information
=================

The Open State Project provides a RESTful API for accessing state legislative information.

  * The base URL is ``http://openstates.sunlightlabs.com/api/``
  * All methods take an optional ``?format=(xml|json)`` parameter: JSON is the default if none is specified.
  * Appropriate HTTP error codes are sent on errors.
  * An API key is required and can be obtained via http://services.sunlightlabs.com/
  * There is a `Python client library <http://github.com/sunlightlabs/python-fiftystates>`_ available.

Methods
=======

State Lookup
------------

Grab metadata about a certain state.

URL format
^^^^^^^^^^

http://openstates.sunlightlabs.com/api/:STATE-ABBREV:/?apikey=YOUR_API_KEY

Response Fields
^^^^^^^^^^^^^^^

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

Example
^^^^^^^

http://openstates.sunlightlabs.com/api/ca/?apikey=YOUR_API_KEY

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


Legislator Lookup
-----------------

If you have the Fifty State Project ``leg_id`` for a specific legislator, you can lookup more information
using this call.

URL Format::
    http://openstates.sunlightlabs.com/api/legislators/:LEG_ID:/?apikey=YOUR_API_KEY

Example::
    http://openstates.sunlightlabs.com/api/legislators/105/?apikey=YOUR_API_KEY

This will return a single object (or an HTTP error if the ID is invalid) with at least the following fields:

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

Legislator Search
-----------------

Searches for legislators matching certain criteria.

Parameters
^^^^^^^^^^

``state``
    Filter by state served in (two-letter state abbreviation)
``first_name`` ``last_name`` ``middle_name``
    Filter by name
``party``
    Filter by the legislator's party, e.g. 'Democrat' or 'Republican'.
``session``
    Filter by legislators who served during a certain session
``district``
    Filter by legislative district

URL format
^^^^^^^^^^
    http://openstates.sunlightlabs.com/api/legislators/search/?:SEARCH-PARAMS:&apikey=YOUR_API_KEY

Example
^^^^^^^
    http://openstates.sunlightlabs.com/api/legislators/search/?state=ca&party=democrat&first_name=Bob&apikey=YOUR_API_KEY

Result will be a list of objects, each containing the same fields returned by :ref:``legislator lookup <leg-lookup>``. If no matching legislators are found, will return an empty list.

District Lookup
---------------

Districts can be looked up by name or by latitude & longitude.

URL Formats::

   http://openstates.sunlightlabs.com/api/:STATE-ABBREV:/:SESSION:/:CHAMBER:/districts/:DISTRICT-NAME:/?apikey=YOUR_API_KEY
   http://openstates.sunlightlabs.com/api/:STATE-ABBREV:/:SESSION:/:CHAMBER:/districts/geo/?lat=:LATITUDE:&long=:LONGITUDE:&apikey=YOUR_API_KEY

Examples::

   http://openstates.sunlightlabs.com/api/ny/2009-2010/upper/districts/10/?apikey=YOUR_API_KEY
   http://openstates.sunlightlabs.com/api/ny/2009-2010/upper/districts/geo/?lat=-73.675451&long=42.73749&apikey=YOUR_API_KEY


Response will be a single object with at least the following fields:

  * ``state``, ``session``, ``chamber``, ``name`` identifying the district
  * ``legislators``: the legislator(s) serving in this district for the requested session
