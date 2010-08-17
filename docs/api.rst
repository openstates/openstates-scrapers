**********************
Open State Project API
**********************

Basic Information
=================

The Open State Project provides a RESTful API for accessing state legislative information.

  * The base URL is ``http://openstates.sunlightlabs.com/api/v1/``
  * All methods take an optional ``?format=(xml|json)`` parameter: JSON is the default if none is specified.
  * Appropriate HTTP error codes are sent on errors.
  * An API key is required and can be obtained via http://services.sunlightlabs.com/
  * There is a `Python client library <http://github.com/sunlightlabs/python-fiftystates>`_ available.


Methods
=======

.. toctree::
    :maxdepth: 2

    State Metadata <api.metadata>
    Bill Methods <api.bills>
    Legislator Methods <api.legislators>
