============
Backend Code
============

The code in this directory is a backend for storing and manipulating Fifty State data in a CouchDB server.

Requirements
------------

* Python 2.5+
* a recent SVN checkout of `CouchDB <http://couchdb.apache.org/>`_
* a recent SVN checkout of `python-couchdb <http://code.google.com/p/couchdb-python/>`_ patched with the ``couchdb-python-fixes.diff`` file in this directory
* `CouchApp <http://github.com/jchris/couchapp/tree/master>`_
* `python-votesmart <http://github.com/sunlightlabs/python-votesmart/tree/master>`_  and an API Key if you want to grab biographical data from `Project Vote Smart <http://www.votesmart.org/>`_
* `argparse <http://code.google.com/p/argparse/>`_

Examples
--------

 $ ./couchimport.py ca

will import scraped data for the state of California into a local CouchDB database.

 $ ./get_bio.py -y 2007 ca

will get biographical data from Project Vote Smart for California state legislators elected in 2007.

 $ ./download_versions.py ca

will download copies of bill text versions into the database as CouchDB attachments.