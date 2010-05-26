=====================
Contributing Scrapers
=====================

If you are interested in contributing your first steps should be checking
the `status page <http://fiftystates-dev.sunlightlabs.com/status/>`_ and emailing
the `Fifty State Project Google Group <http://groups.google.com/group/fifty-state-project>`_
announcing your intention to claim a new state.

After you have announced your intent the process is:

* create a fork of the `fiftystates project on github <http://github.com/sunlightlabs/fiftystates/>`_
* write your scraper in your fork
* get in contact with a committer that will oversee getting your work merged
* once your code has been committed you may ask for commit access to maintain
  changes to your state(s)

.. contents::
   :local:

What All Developers Should Know
===============================

Obtaining Source Code
---------------------

Code can be pulled via git from the following location::

    git://github.com/sunlightlabs/fiftystates.git

You are encouraged to create a `github <http://github.com>`_ account
and create a fork from sunlightlabs' `fiftystate project <http://github.com/sunlightlabs/fiftystates/>`_ code to work off of.
Feel free to send pull requests to `mikejs <http://github.com/mikejs>`_ when
you have working code.

Utilities
---------

All new scrapers should be written in Python, using our :ref:`Python scraping utilities <pythonapi>`.

The preferred library for scraping is `lxml <http://codespeak.net/lxml/>`_ which offers robust support
for several different methods of scraping.  For cases where lxml is not an option (such as scraping from
Text or PDF files) other libraries may be used.

Licensing
---------

The Fifty State Project scrapers are currently licensed under the `GPL 3 <http://gplv3.fsf.org/>`_.
If you would like to submit code under a different license please contact us.

Writing a Parser
================

Creating a New State Parser
---------------------------

If a parser for the state you are working on does not already exist,
you should create a directory under *scripts* and name it after the
official two letter abbreviation of the state name.  The name of the
directory should be written in lowercase.  Each state directory file
should have at least two files.  One file should be called STATUS.
See `Communicating Code Status`_ for information on what should be in this file.
The second file should be an executable that collects and writes the
state legislative data into the *data*/*your state* directory in json,
for an example of this file view *scripts/example/get_legislation.py* or
any of the existing completed states.

Python Parser Tools
-------------------

To aid in development, we have created tools that take care of writing
the data to intermediate json files and provide some utilities that you
may find useful in handling errors and logging.
These tools are located in the *scripts/pyutils* directory, see
the :ref:`pythonapi` for more information.

Running Your Parser
-------------------

When you test your parser please run it from the top level of the
*fiftystates* directory (ie: python ./scripts/ct/get_legislation.py -y
2008 --upper).  This is where we will be running the scripts from and
it will ensure all data gets written to the proper place.  If you use
our skeleton code, it imports the libraries assuming you will be running the
script from the *fiftystates* directory.

.. _STATUS:

Communicating Code Status
-------------------------
Each state submission should have a text file named STATUS in its
state directory.  This file should contain up to date information on
the status of the parser. The following text can be used as a template::

    [California]
    start_year: 2008
    bills: yes
    bill_versions: no
    sponsors: no
    actions: no
    votes: no
    legislators: yes
    committees: no
    contributors: your name, somebody else's name
    contact: wendy@email.com
    notes:

- This file should be written in the style `described here <http://docs.python.org/library/configparser.html>`_
- You should write the full name of the state you are parsing
  in-between the square brackets.
- under **start_year**, you should write the first year you can get
  legislative data from
- **contributors** should be a comma separated list of the names of the people who contributed to the state's scraper.
- **notes** is any notes you have on the code, including any bugs or
  issues.  You should also include information on any extra data you
  may be scraping.
- the remaining values should be *yes*, *no*, or *n/a*. *yes* means you have functionality
   that scrapes that data, *no* means that you have yet to implement
   the functionality or that it is not fully implemented, *n/a* means
   that that data is not available from the state.

If you decide to stop maintaining your script, please send a
message to the `Fifty State Project Google Group
<http://groups.google.com/group/fifty-state-project>`_ so we can find
someone else to take over your states.
