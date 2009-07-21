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

Dependencies
-------------

Regardless of whichever language you choose we prefer that you keep
the number of dependencies to a minimum.  For a list of libraries that
we encourage you to use see :ref:`dependencies`.

Licensing
---------
For licensing information, see :ref:`licensing`.

Obtaining Source Code
---------------------

Code can be pulled via git from the following location:
::
    git://github.com/sunlightlabs/fiftystates.git

You are encouraged to create a `github <http://github.com>`_ account
and create a fork from sunlightlab's `fiftystate project
<http://github.com/sunlightlabs/fiftystates/tree/master>`_ code to work off of.


Writing a Parser
================

Creating a New State Parser
---------------------------

If a parser for the state you are working on does not already exist,
you should create a directory under *scripts* and name it after the
official two letter abbreviation of the state name.  The name of the
directory should be written in lowercase.  Each state directory file
should have at least two files.  One file should be called STATUS.
See `Communicating Code Status`_.. for information on what should be in this file.
The second file should be an executable that collects and writes the
state legislative data into the *data*/*your state* directory in json


Python Parser Tools
-------------------

To aid in development, we have created tools that take care of writing
the data to the database.  The source code of these tools is located
in the *scripts/pyutils* directory, please take a look at the
:ref:`pythonapi` for more information.

For your convenience we have created some stub files that you can
use as a starting point for your parser.  They can be found under
*scripts/python_template*

Running Your Parser
-------------------

When you test your parser please run it from the top level of the
*fiftystates* directory (ie: python ./scripts/ct/get_legislation.py -y
2008 -upper).  This is where we will be running the scripts from and
it will ensure all data gets written to the proper place.  If you use
our skeleton code, it imports the libraries assuming you will be running the
script from the *fiftystates* directory.

Submitting Code
===============

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
    contributors: your name, somebody else's name
    contact: wendy@email.com
    executable: get_legislation.py
    notes:
- This file should be written in the style `described here <http://docs.python.org/library/configparser.html>`_
- You should write the full name of the state you are parsing
  in-between the square brackets.
- under **start_year**, you should write the first year you can get
  legislative data from
- **contributors** should be a comma separated list of the names of the people who contributed to the state's scraper.
- **contact* is the email address of the lead developer
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

State Specific Documentation
----------------------------
If the *notes* section of your STATUS is not enough to express the problems or usage of your scraper, we encourage you to write state specific documentation in ReStructuredText format and hook it into our documentation.  For an example of a state that does that, take a look at *ca*.

Our documentation is generated using `sphinx
<http://sphinx.pocoo.org/>`_.  To link in documentation from your
state, write your documentation up in a `ReStructuredText
<http://docutils.sourceforge.net/rst.html>`_ format in *README.rst* in
your state script directory.  Then add the relative path to your
documentation (without the .rst extension) to
*scripts/state-specific-index.rst*. You can then use the *Makefile*
under the *docs* directory to build and check your documentation.
