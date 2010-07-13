=====================
Contributing Scrapers
=====================

If you are interested in contributing your first steps should be checking
the `status page <http://fiftystates-dev.sunlightlabs.com/status/>`_ and emailing
the `Fifty State Project Google Group <http://groups.google.com/group/fifty-state-project>`_
announcing your intention to claim a new state.

After you have announced your intent the process is:

* create a fork of the `fiftystates project on github <http://github.com/sunlightlabs/fiftystates/>`_
* write your scraper, making commits to your fork
* get in contact with a committer that will oversee getting your work merged
* once your code has been committed you may ask for commit access to maintain
  changes to your state(s)

.. contents::
   :local:

Obtaining Source Code
---------------------

Code can be pulled via git from the following location::

    git://github.com/sunlightlabs/fiftystates.git

You are encouraged to create a `github <http://github.com>`_ account
and create a fork from sunlightlabs' `fiftystate project <http://github.com/sunlightlabs/fiftystates/>`_ code to work off of.
Feel free to send pull requests to `mikejs <http://github.com/mikejs>`_ when you have working code.


Setting Up Your Environment
---------------------------

It is strongly recommended that you install `python-virtualenv <http://pypi.python.org/pypi/virtualenv>`_ and create a "fiftystates" virtualenv.  This allows you to install packages that the project needs without modifying your global python installation.

After creating a virtualenv be sure that the base ``fiftystates`` directory has been added to your path
(the easiest way to do this during development is by running ``python setup.py develop`` in the base ``fiftystates`` directory).

The preferred library for scraping is `lxml <http://codespeak.net/lxml/>`_ which offers robust support
for several different methods of scraping.  For cases where lxml is not an option (such as scraping from
Text or PDF files) other libraries may be used.

Writing a Scraper
-----------------

If you are starting a new state the first step will be to create a subdirectory of ``fiftystates/scrape``
with the two letter postal abbreviation of your state (ie. wy for wyoming).

All code that you write should be within this directory, common files are:

``__init__.py``
    When starting a new state you should first create an ``__init__.py`` that contains a :ref:`metadata dictionary <metadata>`.
``bills.py``
    :ref:`Scraping of bills <bills>`, including sponsorship information, actions, and (optionally) votes. [Required]
``legislators.py``
    :ref:`Scraping of legislators <legislators>`, optionally may scrape committees as well. [Required]
``committees.py``
    :ref:`Scraping of committees <committees>`. Only required if legislators.py does not include scraping committees.
``votes.py``
    :ref:`Scraping of votes <votes>`. Only required if bills.py does not include scraping votes.

When implementing these files be sure to refer to the linked documentation.

Running Your Scraper
--------------------

There is an executable located at ``fiftystates/scrape/runner.py`` that is used to run scrapers
and takes a number of command line options.  View the documentation for :mod:`fiftystates.scrape.runner`
for more detail on available options.

Examples of common usage
""""""""""""""""""""""""

Getting all legislators for New York from the latest session::

    python fiftystates/scrape/runner.py ny --legislators

Getting all committees and bills for Oklahoma from the 204th session::

    python fiftystates/scrape/runner.py ok --committees --bills --session 204


Submitting Your Code
--------------------

When you have working code for your state please submit a pull request via github and/or email the
`Fifty State Project Google Group <http://groups.google.com/group/fifty-state-project>`_ one of the
committers will review your code and integrate it into the repository.

This is also a good time to get commit access to the main repository so that you can continue to maintain
your scraper should anything break.

The Fifty State Project is licensed under the `GPL 3 <http://gplv3.fsf.org/>`_ and by
submitting your code for inclusion you agree to allow your code to be distributed under this license.
