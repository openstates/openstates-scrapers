===========
Data Format
===========

This directory exists to be populated by the various scripts. Each state should have a toplevel directory named after the two-letter state abbreviation.

State Metadata
--------------

In each state's directory should be a file ``state_metadata.json``. This file should contain a single object with at least the following required fields:

* ``state_name``: the name of this state, e.g. ``"Pennsylvania"``
* ``legislature_name``: the name of the state legislature, e.g. ``"Pennsylvania General Assembly"``
* ``upper_chamber_name`` and ``lower_chamber_name``: the names of the chambers of the state legislature, e.g. ``"Senate"``, ``"House of Representatives"``
* ``upper_title`` and ``lower_title``: the title that members of each chamber hold, e.g. "Senator", "Representative"
* ``upper_term`` and ``lower_term``: the length in years of a term in each chamber, e.g. ``2``, ``4``
* ``sessions``: a chronological listing of valid sessions, e.g. ``['2005-2006', '2007-2008', '2009-2010']`` or ``['81st', '82nd', '83rd']``
* ``session_details``: a dictionary with an entry for each session with the following attributes:

 - ``years``: a list of the years this session covers, e.g. ``[2007]`` or ``[2007, 2008]`` 
 - ``sub_sessions``: a list of special/sub sessions associated with this session, e.g. ``['2001 Special Session #1', '2001 Special Session #2']`` or ``[]``

Bills
-----

Underneath the state's directory should be a 'bills' directory with a separate JSON file for each scraped bill. Each file should contain a single object with the following required fields:

* ``bill_id``: the identifier given to this bill by the state, e.g. ``"H.B. 101"``, ``"S 2"``
* ``session``: the session in which this bill was introduced
* ``chamber``: the chamber in which this bill was introduced, ``"upper"`` or ``"lower"``
* ``title``: a title or description given to this bill by the state
* ``sponsors``: a list of legislators who sponsor this bill. Each entry should be an object with at least the following required fields:

 - ``name``: the name of the sponsor
 - ``type``: the type of sponsorship, e.g. ``"primary"``, ``"cosponsor"``

* ``actions``: a (chronological if possible) list of 'actions' that were performed in relation to this bill. Each entry should be an object with at least the following required fields:

 - ``date``: the date/time the action was performed
 - ``actor``: the person/body/office which performed the action. If the action is associated with either chamber, ``"upper"`` or ``"lower"``. Other possibilities may include ``"Governor"``, ``"Senate Finance Committee"``, etc.
 - ``action``: what happened, e.g. ``"Introduced"``, ``"Referred to Committee X"``, ``"Signed"``

* ``votes``: a (chronological if possible) list of votes associated with this bill. Each entry should be an object with at least the following required fields:

 - ``chamber``: the chamber where the vote took place, ``"upper"`` or ``"lower"``
 - ``date``: the date/time when the vote was taken
 - ``motion``: a string representing the motion that was being voted on
 - ``passed``: boolean, did the vote pass or
 - ``yes_count``, ``no_count``: the number of 'yes' and 'no' votes
 - ``other_count``: the number of (non-)votes not covered by 'yes' or 'no' (such as abstentions)
 - ``yes_votes``, ``no_votes``, ``other_votes``: a list of votes of each type. Each entry should be an object with at least the following required fields:

  - ``name``: the name of the legislator

Legislators
-----------

Underneath the state's directory should be a 'legislators' directory with a separate JSON file for each legislator. Note that legislators who have served multiple terms should have a separate file for each session they served in. Each file should contain a single object with the following required fields:

* ``session``: the session in which this legislator served
* ``chamber``: the chamber in which this legislator served, 'upper' or 'lower'
* ``district``: the district this legislator is representing, as given by the state, e.g. 'District 2', '7th', 'District C'.
* ``full_name``: the full name of this legislator
* ``first_name``: the first name of this legislator
* ``last_name``: the last name of this legislator
* ``middle_name``: a middle name or initial of this legislator, empty string if none is provided
