=============
API Changelog
=============

When we make changes to the API we will document them here.  Backwards incompatible changes will be rare and will result in a change to the current version number as specified as part of the base URL.

The `current API version </api.html>`_ is v1, released on September 1st 2010.

Changes made to Version 1
=========================

* no changes have been made since the release of version 1

Deprecated Versions
===================

Version 0
---------

A pre-release version of the API, currently deprecated and will be removed in November 2010.

Migration to Version 1
^^^^^^^^^^^^^^^^^^^^^^

Most methods of version 0 are available in version 1:

Metadata
    Old URL: http://openstates.sunlightlabs.com/api/:STATE:/

    New URL: http://openstates.sunlightlabs.com/api/v1/metadata/:STATE:/

Bill Lookup
    Old URL: http://openstates.sunlightlabs.com/api/:STATE:/:SESSION:/:CHAMBER:/bills/:BILL_ID:/

    New URL: http://openstates.sunlightlabs.com/api/v1/bills/:STATE:/:SESSION:/:CHAMBER:/:BILL_ID:/

Bill Search
    Old URL: http://openstates.sunlightlabs.com/api/bills/search/?query

    New URL: http://openstates.sunlightlabs.com/api/v1/bills/?query

    Additionally bill search no longer requires a ``q`` parameter if others are specified.

Legislator Lookup
    Old URL: http://openstates.sunlightlabs.com/api/legislators/:ID:/

    New URL: http://openstates.sunlightlabs.com/api/v1/legislators/:ID:/

Legislator Search
    Old URL: http://openstates.sunlightlabs.com/api/legislators/search/?query

    New URL: http://openstates.sunlightlabs.com/api/v1/legislators/?query

Committees Lookup
    Old URL: http://openstates.sunlightlabs.com/api/committees/:ID:/

    New URL: http://openstates.sunlightlabs.com/api/v1/committees/:ID:/
