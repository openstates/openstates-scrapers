**********************
Open State Project API
**********************

Basic Information
=================

The Open State Project provides a RESTful API for accessing state legislative information.

  * The base URL is ``http://openstates.sunlightlabs.com/api/v1/``
  * All methods return JSON, XML output is not currently supported.
  * Appropriate HTTP error codes are sent on errors (generally 404 if object is not found, 401 if authentication fails, etc.).
  * An API key is required and can be obtained via http://services.sunlightlabs.com/
  * There is a `Python client library <http://github.com/sunlightlabs/python-openstates>`_ available.

All changes to the API will be announced on the `Open State Project Google Group <http://groups.google.com/group/fifty-state-project/>`_ and documented in the :doc:`api.changelog`.

Methods
=======

.. toctree::
    :maxdepth: 2

    State Metadata <api.metadata>
    Bill Methods <api.bills>
    Legislator Methods <api.legislators>
    Committee Methods <api.committees>
    Event Methods <api.events>

.. _status:

State Status
============

.. image:: http://s3.amazonaws.com/assets.sunlightlabs.com/openstates/v1/images/openstatesmap.png
    :width: 570
    :height: 441
    :align: right

States in the API are either considered to be "ready" or "experimental".  All states have vetted data that we believe to be of high quality, but experimental states may have incomplete data where we haven't yet identified a source or done manual reconciliation of ids.

If you encounter issues using data from these states please report them on `the Open State Project issue tracker <http://code.google.com/p/openstates/issues/list>`_.

Current Ready States
~~~~~~~~~~~~~~~~~~~~
* California
* Louisiana
* Maryland
* New Jersey
* Texas
* Wisconsin

Current Experimental States
~~~~~~~~~~~~~~~~~~~~~~~~~~~
* Alaska
* Arizona
* Florida
* Minnesota
* Mississippi
* Nevada
* North Carolina
* Pennsylvania
* South Dakota
* Utah
* Vermont
* Virginia

.. note::
    There is essentially no way to guarantee that data is error-free as the very nature of scraping state legislative data from uncooperative websites means that there is always potential for error.  Keep this in mind when using data whether it is from a "ready" or "experimental" state.

Unsupported States (grey)
~~~~~~~~~~~~~~~~~~~~~~~~~

All states not marked are unsupported.  Some of them may have data in the API as we work on getting them to the experimental phase, but it should be noted that we do not make a committment to run their scrapers regularly so data may be outdated or incorrect.  Bugs filed against unsupported states are generally not given any attention until they are at least promoted to experimental.

If you'd like to help move a state from unsupported to experimental please speak up on the `google group <http://groups.google.com/group/fifty-state-project>`_ as we'd be happy to work with you to get a state into the API.

.. _extrafields:

Extra Fields
============

You may notice that the fields documented methods are sometimes a subset of the fields actually included in a response.

Many times as part of our scraping process we take in data that is available for a given state and is either not available or does not have an analog in other states.  Instead of artificially limiting the data we provide to the smallest common subset we make this extra data available.

To make it clear which fields can be relied on and which are perhaps specific to a state or subset of states we prefix non-standard fields with a ``+``.

If you are using the API to get data for multiple states it is best to restrict your usage to the fields documented here, if you are only interested in data for a small subset of our available states it might make sense to take a more in depth look at the API responses for the state in question to see what extra data we are able to provide.
