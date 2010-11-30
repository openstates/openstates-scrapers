=================
Event API Methods
=================

.. contents::
    :depth: 2
    :local:

Event Fields
============

All event methods return Event objects consisting of at least the following fields:

  * ``id``: An Open State Project event id, e.g. ``TXE00004925``
  * ``description``: A description of the event, e.g. 'Appropriations Committee Meeting'
  * ``when``: The date/time of the event, in UTC
  * ``end``: The end date/time of the event, in UTC, if available
  * ``location``: Where the event occurred, e.g. 'Capitol Room 6C
  * ``type``: The type of event, e.g. 'committee:meeting', 'bill:action'
  * ``state``: The state in which the event ocurred
  * ``session``: The legislative session during which the event ocurred
  * ``participants``: A list of people/groups that participated in the event, containing at least the following fields:
    
    * ``type``: the type of participant, e.g. ``legislator`` or ``committee``
    * ``participant`` the name of the participant


Event Search
============

Searches for events matching certain criteria.

Parameters
----------

``state``
    Filter by state (two-letter abbreviation)
``type``
    Filter by event type (e.g.  'committee:meeting'). Accepts multiple types separated by commas.
``format``
    Output format. Possible values: ``json``, ``rss``, ``ics``
   
URL Format
----------

:samp:`http://openstates.sunlightlabs.com/api/v1/events/?{SEARCH-PARAMS}&apikey={YOUR_API_KEY}`

Example
-------

http://openstates.sunlightlabs.com/api/v1/events/?state=tx&type=committee:meeting&apikey=YOUR_API_KEY

::

    [
        {
            "end": null, 
            "description": "Committee Meeting\nState Affairs - 11/15/2010\nTime: 9:00 AM, Location: Senate Chamber", 
            "created_at": "2010-10-12 17:25:50", 
            "when": "2010-11-15 15:00:00", 
            "updated_at": "2010-10-12 17:25:50", 
            "sources": [
                {
                    "url": "http://www.capitol.state.tx.us/MyTLO/RSS/RSS.aspx?Type=upcomingmeetingssenate", 
                    "retrieved": "2010-10-12 16:09:27"
                }
            ], 
            "state": "tx", 
            "session": "811", 
            "location": "Senate Chamber", 
            "type": "committee:meeting", 
            "participants": [
                {
                    "type": "committee", 
                    "participant": "State Affairs"
                }
            ], 
            "+link": "http://www.legis.state.tx.us/tlodocs/81R/schedules/html/C5702010111509001.htm", 
            "id": "TXE00000078"
        }, 
        {
            "end": null, 
            "description": "Committee Meeting\nInsurance - 10/28/2010\nTime: 10:30 AM, Location: E1.026", 
            "created_at": "2010-10-12 17:25:50", 
            "when": "2010-10-28 16:30:00", 
            "updated_at": "2010-10-12 17:25:50", 
            "sources": [
                {
                    "url": "http://www.capitol.state.tx.us/MyTLO/RSS/RSS.aspx?Type=upcomingmeetingshouse", 
                    "retrieved": "2010-10-12 16:09:27"
                }
            ], 
            "state": "tx", 
            "session": "811", 
            "location": "E1.026", 
            "type": "committee:meeting", 
            "participants": [
                {
                    "type": "committee", 
                    "participant": "Insurance"
                }
            ], 
            "+link": "http://www.legis.state.tx.us/tlodocs/81R/schedules/html/C3202010102810301.htm", 
            "id": "TXE00000091"
        }, 
    .
    .
    .
    ]
    
    
Event Lookup
============

Looks up information on a single legislative event given its Open State Project event ID.

URL Format
----------

:samp:`http://openstates.sunlightlabs.com/api/v1/events/{EVENT_ID}/?apikey={YOUR_API_KEY}`

Example
-------

http://openstates.sunlightlabs.com/api/v1/events/TXE00004925/?apikey=YOUR_API_KEY

::

    {
        "end": null, 
        "description": "Committee Meeting\nInsurance - 10/28/2010\nTime: 10:30 AM, Location: E1.026", 
        "created_at": "2010-10-12 17:25:50", 
        "when": "2010-10-28 16:30:00", 
        "updated_at": "2010-10-12 17:25:50", 
        "sources": [
            {
                "url": "http://www.capitol.state.tx.us/MyTLO/RSS/RSS.aspx?Type=upcomingmeetingshouse", 
                "retrieved": "2010-10-12 16:09:27"
            }
        ], 
        "state": "tx", 
        "session": "811", 
        "location": "E1.026", 
        "type": "committee:meeting", 
        "participants": [
            {
                "type": "committee", 
                "participant": "Insurance"
            }
        ], 
        "+link": "http://www.legis.state.tx.us/tlodocs/81R/schedules/html/C3202010102810301.htm", 
        "id": "TXE00000091"
    }