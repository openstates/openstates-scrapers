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
``terms``
    A list of terms that we have data available for. Each session will be an object with the following fields:
    * ``start_year``: The year in which this session began.
    * ``end_year``: The year in which this session ended.
    * ``name``: The name of this session.
    * ``sessions``: List of sessions that took place inside the given term.
``session_details``
    Optional extra details about sessions.

    If present will be a dictionary with keys corresponding to ``sessions`` and values are dictionaries
    of extra metadata about a session.

    Fields that may be present include ``start_date`` and ``end_date``.



URL format
----------

:samp:`http://openstates.sunlightlabs.com/api/v1/metadata/{STATE-ABBREV}/?apikey={YOUR_API_KEY}`


Example
-------

http://openstates.sunlightlabs.com/api/v1/metadata/ca/?apikey=YOUR_API_KEY

::

 {
     "lower_chamber_title": "Assemblymember",
     "lower_chamber_name": "Assembly",
     "upper_chamber_title": "Senator",
     "terms": [
         {
             "end_year": 2010,
             "start_year": 2009,
             "+start_date": 1228089600.0,
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
     "session_details": {
         "20092010 Special Session 5": {
             "type": "special"
         },
         "20092010 Special Session 4": {
             "type": "special"
         },
         "20092010 Special Session 7": {
             "type": "special"
         },
         "20092010 Special Session 6": {
             "type": "special"
         },
         "20092010 Special Session 1": {
             "type": "special"
         },
         "20092010 Special Session 3": {
             "type": "special"
         },
         "20092010 Special Session 2": {
             "type": "special"
         },
         "20092010": {
             "type": "primary",
             "start_date": "2008-12-01 00:00:00"
         },
         "20092010 Special Session 8": {
             "type": "special"
         }
     },
     "legislature_name": "California State Legislature",
     "lower_chamber_term": 2
 }
