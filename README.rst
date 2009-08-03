=======================
Overview
=======================

If you are reading this page on github, please go `here <http://samburg.sunlightlabs.com/docs>`_ to read more complete documentation.

About the Project
=================

The goal of the Fifty State Project is to build scrapers and parsers in order to get as much state 
legislative data as possible in one place.

For details on the reasons for the project and goals behind the project see 
`the project announcement <http://sunlightlabs.com/blog/2009/02/26/fifty-state-project/>`_.

To stay up to date and communicate with other contributors to the project visit the `Fifty State Project Google Group <http://groups.google.com/group/fifty-state-project>`_.

For an editable overview of each state's progress visit the `Sunlight Labs Wiki <http://wiki.sunlightlabs.com/index.php/State_Legislation_Page>`_.

Project Goals
-------------

1. Collect URLs of State Legislature and Legislative Information Pages [done]
2. Grab legislators and legislation
     1. Build scrapers and obtain data files for legislation in each of the fifty states
     2. create sponsor relationship between legislators and legislation 
3. Grab votes
     1. Build scrapers and obtain data files for legislator votes on legislation
     2. create voting relationship between legislators and legislation 
4. Build tools on top of data 


.. _usage:

Usage (proposed)
----------------
Valid options:
 * ``--year``: a year or years the parser should attempt
 * ``--all``: Attempt to parse years from 1969-2009
 * ``--upper``: Parse upper chamber
 * ``--lower``: Parse lower chamber
 
The vision is that the flow will look something like this:
    $  ./scripts/nc/get_legislation --year=2009 --upper


Contributing
============

If you are interested in contributing the recommended procedure is to
check on the `Sunlight Labs Wiki
<http://wiki.sunlightlabs.com/index.php/Fifty_State_Project#Status>`_
and in the repository to see where your state is.  The next step is to
announce your interest on the `Fifty State Project Google Group
<http://groups.google.com/group/fifty-state-project>`_ (this is where
you can ask questions and make suggestions regarding the project).

Managing a State
----------------

Once you have claimed a state on the wiki and mailing list you should probably 
maintain your own fork of the project on `github <http://github.com>`_.

Please avoid making changes to files in other states/etc. on your state branch.
Stick to editing files in the scripts/*your_state* directory and where necessary 
in any relevant utils directories.

Whenever your state script works as it should announce it on the mailing list and 
someone will merge your changes into the core.

.. _licensing:

Licensing
---------

As of June 15th 2009 the Fifty State Project is licensed under the `GPLv3 license <http://www.fsf.org/licensing/licenses/gpl-3.0.html>`_

See LICENSING for the full terms of the GPLv3.

Requirements
============

Although we have previously allowed you to write parsers in your
language of choice, for the sake of maintenance we *highly* encourage
you to write your parsers in Python. Currently Python is the only
language we are supporting with our documentation and tools.  If you
would like to contribute in a language other than Python, please send
an email to `Fifty State Project Google Group
<http://groups.google.com/group/fifty-state-project>`_ so we can
discuss the issue.

For details on how scripts should be written and how they should run see :doc:`scripts/pyutils/README`.

If you are completely unfamiliar with Python there is other things you
can do to help with the government transparency movement.  Ruby developers are encouraged to work on the `Congrelate <http://congrelate.com>`_ Project.  For other project ideas please join the `Sunlight Labs Google Group <http://groups.google.com/group/sunlightlabs>`_.


.. _dependencies:

Dependencies
-------------
* Python (2.5+)
* BeautifulSoup
* html5lib
* simplejson if on Python 2.5
* (this list is out of date, refer to specific scripts/state directories for dependencies)

