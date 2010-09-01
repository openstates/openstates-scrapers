==========
API Status
==========

This page will always reflect the latest official status of states in the API.  States are either categorized as ready (green), experimental (orange), or unsupported (grey).


State Status
============

.. image:: /_static/apimap.png
    :width: 576
    :height: 352

Ready States (green)
--------------------

States considered ready have high quality scrapers that are run regularly while the chamber in question is in session.  

Issues reported with ready states are considered of high priority.  If you encounter issues using data from these states please report them on `the Open State Project issue tracker <http://code.google.com/p/openstates/issues/list>`_.

.. note::
    Ready should not be confused with perfect.  There is essentially no way to guarantee that data is error-free as the very nature of scraping state legislative data from uncooperative websites means that there is always potential for error.

Current Ready States
~~~~~~~~~~~~~~~~~~~~
* California
* Louisiana
* Maryland
* Texas
* Wisconsin

Experimental States (orange)
----------------------------

States marked experimental are lower priority when it comes to bug fixes, but are still believed by us to have high quality data available.  Also we may not have added some of our added-value fields (bill/vote/action types, alternate legislator ids, etc.).

We encourage you to experiment with experimental states and not be shy about reporting bugs in the `the Open State Project issue tracker <http://code.google.com/p/openstates/issues/list>`_.  (Just be aware that it may be slightly longer before we are able to address issues with experimental states.)

Generally we try to run experimental state scrapers as often as ready states, though there may be brief periods where the data is not updated daily.

Current Experimental States
~~~~~~~~~~~~~~~~~~~~~~~~~~~
* Nevada
* North Carolina
* Pennsylvania
* South Dakota
* Vermont

Unsupported States (grey)
-------------------------

All states not marked are unsupported.  Some of them may have data in the API as we work on getting them to the experimental phase, but it should be noted that we do not make a committment to run their scrapers regularly so data may be outdated or incorrect.  Bugs filed against unsupported states are generally not given any attention until they are at least promoted to experimental.

If you'd like to help move a state from unsupported to experimental please speak up on the `google group <http://groups.google.com/group/fifty-state-project>`_ as we'd be happy to work with you to get a state into the API.
