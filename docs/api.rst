=======================
Fifty State Project API
=======================


.. contents::
   :local:

Basic Information
=================

The Fifty State Project provides a RESTful API for accessing state legislative information.

* The base URL is ``http://fiftystates-dev.sunlightlabs.com/api/``.
* All methods take an optional ``?format=(xml|json)`` parameter: JSON is the default if none is specified.
* Appropriate HTTP error codes are sent on errors.
* An API key is required and can be obtained `here <http://services.sunlightlabs.com/>`_
* There is a :doc:`Python client library <client>`

Methods
=======

.. _state-metadata:

State Lookup
------------

Grab metadata about a certain state.

URL format::

	http://fiftystates-dev.sunlightlabs.com/api/:STATE-ABBREV:/?apikey=YOUR_API_KEY

Example::

	http://fiftystates-dev.sunlightlabs.com/api/ca/?apikey=YOUR_API_KEY

The response will be an object including at least the following fields:

* ``name``: The name of the state
* ``abbreviation``: The two-letter abbreviation of the state
* ``legislature_name``: The name of the state legislature
* ``upper_chamber_name``: The name of the 'upper' chamber of the state legislature (if applicable)
* ``lower_chamber_name``: The name of the 'lower' chamber of the state legislature (if applicable)
* ``upper_chamber_term``: The length, in years, of a term for members of the 'upper' chamber (if applicable)
* ``lower_chamber_term``: The length, in years, of a term for members of the 'lower' chamber (if applicable)
* ``upper_chamber_title``: The title used to refer to members of the 'upper' chamber (if applicable)
* ``lower_chamber_title``: The title used to refer to members of the 'lower' chamber (if applicable)

* ``sessions``: A list of sessions that we have data available for. Each session will be an object with the following fields:
	* ``start_year``: The year in which this session began.
	* ``end_year``: The year in which this session ended.
	* ``name``: The name of this session.

.. _bill-lookup:

Bill Lookup
-----------

Get information about a specific bill.

URL Format::

	http://fiftystates-dev.sunlightlabs.com/api/:STATE-ABBREV:/:SESSION:/:CHAMBER:/bills/:BILL-ID:/?apikey=YOUR_API_KEY

Example::

	http://fiftystates-dev.sunlightlabs.com/api/ca/20092010/lower/bills/AB667/?apikey=YOUR_API_KEY

Response will be an object with the following fields:

* ``title``: The title given to the bill by the state legislature
* ``state``: The state this bill is from
* ``session``: The session this bill was introduced in
* ``chamber``: The chamber this bill was introduced in (e.g. 'upper', 'lower')
* ``bill_id``: The identifier given to this bill by the state legislature (e.g. 'AB6667')
* ``actions``: A list of legislative actions performed on this bill. Each action will be an object with at least the following fields:

	* ``date``: The date/time the action was performed
	* ``actor``: The chamber, person, committee, etc. responsible for this action
	* ``action``: A textual description of the action performed

* ``sponsors``: A list of sponsors of this bill. Each sponsor will be an object with at least the following fields:

	* ``leg_id``: A Fifty State Project legislator ID (see :ref:`legislator lookup <leg-lookup>`)
	* ``full_name``: The name of the sponsor
	* ``type``: The type of sponsorship (state specific, examples include 'Primary Sponsor', 'Co-Sponsor')

* ``votes``: A list of votes relating to this bill. Each vote will be an object with at least the following fields:

	* ``date``: The date/time the vote was taken
	* ``chamber``: The chamber that the vote was taken in
	* ``motion``: The motion being voted on
	* ``yes_count``, ``no_count``, ``other_count``: The number of 'yes', 'no', and other votes
	* ``passed``: Whether or not the vote passed

* ``versions``: A list of versions of the text of this bill. Each version will be an object with at least the following fields:

	* ``url``: The URL for an official source of this version of the bill text
	* ``name``: A name for this version of the bill text

Bill Search
-----------

Search bills by keywords.

URL Format::

    http://fiftystates-dev.sunlightlabs.com/api/bills/search/?:SEARCH-PARAMS:&apikey=YOUR_API_KEY

Example::

    http://fiftystates-dev.sunlightlabs.com/api/bills/search/?q=agriculture&state=vt&apikey=YOUR_API_KEY

Possible search parameters include:

* ``q`` (required): the keyword string to lookup
* ``state`` (optional): filter results by given state (two-letter abbreviation)
* ``session`` (optional): filter results by given session
* ``chamber`` (optional): filter results by given chamber ('upper' or 'lower')
* ``updated_since`` (optional): only return bills that have been
  updated since a given date, YYYY-MM-DD format

Returns a list of bills containing the same fields returned by  :ref:`bill lookup <bill-lookup>`. Will only return the first 20 matching bills. If no bills match, a blank list is returned.

Latest Bills
------------

Get bills updated since a certain time

URL Format::

    http://fiftystates-dev.sunlightlabs.com/api/bills/latest/?updated_since=:TIMESTAMP:&state=:STATE-ABBREV:&apikey=YOUR_API_KEY

Example::

    http://fiftystates-dev.sunlightlabs.com/api/bills/latest/?updated_since=2010-04-01&state=sd&apikey=YOUR_API_KEY

Required parameters:

* ``updated_since``: how far back to search, in YYYY-MM-DD format
* ``state``: the state to search (two-letter abbreviation)
    
.. _leg-lookup:

Legislator Lookup
-----------------

If you have the Fifty State Project ``leg_id`` for a specific legislator, you can lookup more information
using this call.

URL Format::

	http://fiftystates-dev.sunlightlabs.com/api/legislators/:LEG_ID:/?apikey=YOUR_API_KEY

Example::

	http://fiftystates-dev.sunlightlabs.com/api/legislators/105/?apikey=YOUR_API_KEY

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

.. _leg-search:

Legislator Search
-----------------

Searches for legislators matching certain criteria. Search paramaters can include any combination
of:

* ``state``: Filter by state served in (two-letter state abbreviation)
* ``first_name``, ``last_name``, ``middle_name``: Filter by name
* ``party``: Filter by the legislator's party, e.g. 'Democrat' or 'Republican'.
* ``session``: Filter by legislators who served during a certain session
* ``district``: Filter by legislative district

URL format::

	http://fiftystates-dev.sunlightlabs.com/api/legislators/search/?:SEARCH-PARAMS:&apikey=YOUR_API_KEY

Example::

	http://fiftystates-dev.sunlightlabs.com/api/legislators/search/?state=ca&party=democrat&first_name=Bob&apikey=YOUR_API_KEY

Result will be a list of objects, each containing the same fields returned by :ref:`legislator lookup <leg-lookup>`. If no matching legislators are found, will return an empty list.

.. _vote-lookup:

District Lookup
---------------

Districts can be looked up by name or by latitude & longitude.

URL Formats::

   http://fiftystates-dev.sunlightlabs.com/api/:STATE-ABBREV:/:SESSION:/:CHAMBER:/districts/:DISTRICT-NAME:/?apikey=YOUR_API_KEY
   http://fiftystates-dev.sunlightlabs.com/api/:STATE-ABBREV:/:SESSION:/:CHAMBER:/districts/geo/?lat=:LATITUDE:&long=:LONGITUDE:&apikey=YOUR_API_KEY

Examples::

   http://fiftystates-dev.sunlightlabs.com/api/ny/2009-2010/upper/districts/10/?apikey=YOUR_API_KEY
   http://fiftystates-dev.sunlightlabs.com/api/ny/2009-2010/upper/districts/geo/?lat=-73.675451&long=42.73749&apikey=YOUR_API_KEY

Response will be a single object with at least the following fields:

* ``state``, ``session``, ``chamber``, ``name`` identifying the district
* ``legislators``: the legislator(s) serving in this district for the requested session
