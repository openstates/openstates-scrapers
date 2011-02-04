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

The current status of various state data in the API can be obtained via the :doc:`api.status` page.

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

.. _extrafields:

Extra Fields
============

You may notice that the fields documented methods are sometimes a subset of the fields actually included in a response.

Many times as part of our scraping process we take in data that is available for a given state and is either not available or does not have an analog in other states.  Instead of artificially limiting the data we provide to the smallest common subset we make this extra data available.

To make it clear which fields can be relied on and which are perhaps specific to a state or subset of states we prefix non-standard fields with a ``+``.

If you are using the API to get data for multiple states it is best to restrict your usage to the fields documented here, if you are only interested in data for a small subset of our available states it might make sense to take a more in depth look at the API responses for the state in question to see what extra data we are able to provide.
