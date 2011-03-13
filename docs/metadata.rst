===============
State Metadata
===============

The top level directory for a scraper should include an ``__init__.py`` that has a ``metadata`` dictionary.

This file should include the basic details on the state, most importantly the terms and sessions for which the scraper can be run for.

Metadata Fields
===============

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
``latest_dump_url``
    URL pointing to a download of all data for the state
``latest_dump_date``
    datestamp of the file at ``latest_dump_url``
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

    Fields that may be present include ``start_date`` and
    ``end_date``, as well as ``type`` indicating whether the session
    was a normally scheduled or special session.

Example
-------

Example data for Maryland::

    import datetime

    metadata = dict(
        name='Maryland',
        abbreviation='md',
        legislature_name='Maryland General Assembly',
        upper_chamber_name='Senate',
        lower_chamber_name='House of Delegates',
        upper_chamber_title='Senator',
        lower_chamber_title='Delegate',
        upper_chamber_term=4,
        lower_chamber_term=4,
        terms=[
            {'name': '2007-2010', 'sessions': ['2007', '2007s1', '2008',
                                               '2009', '2010'],
             'start_year': 2007, 'end_year': 2010},
            {'name': '2011-2014', 'sessions': ['2011'],
             'start_year': 2011, 'end_year': 2014},
        ],
        session_details={
            '2007': {'start_date': datetime.date(2007,1,10),
                     'end_date': datetime.date(2007,4,10),
                     'number': 423,
                     'type': 'primary'},
            '2007s1': {'start_date': datetime.date(2007,10,29),
                       'end_date': datetime.date(2007,11,19),
                       'number': 424,
                       'type': 'special'},
            '2008': {'start_date': datetime.date(2008,1,9),
                     'end_date': datetime.date(2008,4,7),
                     'number': 425,
                     'type': 'primary'},
            '2009': {'start_date': datetime.date(2009,1,14),
                     'end_date': datetime.date(2009,4,13),
                     'number': 426,
                     'type': 'primary'},
            '2010': {'start_date': datetime.date(2010,1,13),
                     'end_date': datetime.date(2010,4,12),
                     'number': 427,
                     'type': 'primary'},
            '2011': {'start_date': datetime.date(2011,1,12),
                     'end_date': datetime.date(2011,4,12),
                     'number': 428,
                     'type': 'primary'},
        },
    )

