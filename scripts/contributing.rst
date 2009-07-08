================
Getting Started 
================ 

If you are interested in contributing the recommended procedure is to
check on the `Sunlight Labs Wiki
<http://wiki.sunlightlabs.com/index.php/Fifty_State_Project#Status>`_
and in the repository to see where your state is.  The next step is to
announce your interest on the `Fifty State Project Google Group
<http://groups.google.com/group/fifty-state-project>`_ (this is where
you can ask questions and make suggestions regarding the project).

What All Developers Should Know
==============================

Choosing a Language
-------------------
It is preferred for the sake of maintenance that scripts are written in 
Python, several Ruby scripts also exist if you are unfamiliar with Python.

If you are completely unfamiliar with Python or Ruby writing a scraper in
another language is preferred over not contributing at all but given the
number of scripts already written in Python you are strongly encouraged to
consider it first.

Dependencies
-------------

Regardless of whichever language you choose we prefer that you keep
the number of dependencies to a minumum.  For a list of libaries that
we encourage you to use see :ref:`python-dependencies`.



Licensing
---------
For licensing information, see :ref:`licensing`.


Obtaining Source Code
---------------------

Code can be pulled via git from the following location:
::
    git://github.com/sunlightlabs/fiftystates.git

You are encoraged to create a `github <http://github.com>`_ account
and create a fork from sunlightlab's `fiftystate project
<http://github.com/sunlightlabs/fiftystates/tree/master>`_ code to work off of.

Creating a New State Parser
---------------------------

If a parser for the state you are working on does not already exist,
you should create a directory under *scripts* and name it after the
offical two letter abbreviation of the state name.  The name of the
directory should be written in lowercase.  Each state directory file
should have at least two files.  One file should be called STATUS.
See :ref:`STATUS`. for information on what should be in this file.
The second file should be an executable that collects and writes the
state legilative data into the *data*/*your state* directory in json
format.   See :ref:`database` for more information on how to structure
you data.  If you are using our Python or Ruby tools you do not need
to worry on how to structure that data you collect because our tools
write the database files for you.

Submitting Code
---------------


.. _STATUS:
Communicating Code Status
-------------------------
Each state submission should have a text file named STATUS in its
state directory.  This file should contain up to date information on
the status of the parser. The following text can be used as a template
::
    [California]
    start_year: 2008
    bills: no
    bill_versions: no
    sponsors: no
    actions: no
    votes: no
    contributors: your name <your@email.com>
    executable: get_legislation.py
    notes:

- You should write the full name of the state you are parsing
  in-between the square brackets.
- under **start_year**, you should write the first year you can get
  legislative data from
- **contributers** should be a comma seperated list of the names and
   emails of people who contributed to the state's scraper.
- **notes** is any notes you have on the code, including any bugs or
  issues.  You should also include information on any extra data you
  may be scraping.
- **executable** should be the name or path (relative to the state's
    directory) to the executable file that does all of the work (data
    collection and writing the json files).
- **bills**, **bill_versions**, **sponsors**, **actions**, and **votes** should be
   followed by *yes*, *no*, or *n/a*. *yes* means you have functionality
   that scrapes that data, *no* means that you have yet to implement
   the functionality or that it is not fully implemented, *n/a* means
   that that data is not available from the state.

If you ever decide to stop maintaining your script, please send a
message to the `Fifty State Project Google Group
<http://groups.google.com/group/fifty-state-project>`_ so we can find
someone else to take over your states.

Writing a Parser in Python
==========================
If you choose to write your parser in Python, we have created some
tools that take care of writing data to the database.  The source code
of these tools is located in the *scripts/pyutils* directory

For your convience we have created some stub files that you can edit
and flesh out for your parser.  They can be found under
*scripts/python_template*


Writing a Parser in Ruby
==========================
If you choose to write your parser in Python, we have created some
tools that take care of writing data to the database.  The source code
of these tools is located in the *scripts/rbutils* directory

Writing a Parser in Some Other Language
======================================= 

If you chose to write your parser in a language other than Python and
Ruby, please conform to our usage and output standards. See
:ref:`usage` to see what the interface of your executable should
be. See :ref:`database` for information on how to structure your data.
