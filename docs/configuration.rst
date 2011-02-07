===================
Billy Configuration
===================

Billy has a global configuration object at :data:`billy.conf.settings` that is used in scraping, import, and serving the API.

If billy finds a module named :mod:`billy_settings` on the global import path it will import that module.  Values found in a custom
:mod:`billy_settings` will override all default settings.  It is also possible to provide custom settings by adding additional all-caps variables
in your custom :mod:`billy_settings`.

.. module:: billy.conf

Default Settings
================

:data:`MONGO_HOST`
    Host or IP address of MongoDB server. (default: "localhost")
:data:`MONGO_PORT`
    Port for MongoDB server. (default: "27017")
:data:`MONGO_DATABASE`
    MongoDB database name. (default: "fiftystates")
:data:`BILLY_DATA_DIR`
    Directory where scraped data should be stored.  (default: "../../data")
:data:`BILLY_CACHE_DIR`
    Directory where scraper cache should be stored.  (default: "../../cache")
:data:`BILLY_ERROR_DIR`
    Directory where scraper error dumps should be stored.  (default: "../../errors")
:data:`SCRAPELIB_TIMEOUT`
    Value (in seconds) for url retrieval timeout.  (default: 600)
:data:`SCRAPELIB_RETRY_ATTEMPTS`
    Number of retries to make if an unexpected failure occurs when downloading a URL.  (default: 3)
:data:`SCRAPELIB_RETRY_WAIT_SECONDS`
    Number of seconds to wait between initial attempt and first retry.  (default: 20)


Command-Line Overrides
======================

Most available scripts can override the above default settings with command line switches:

.. option:: -d <data_dir>, --data_dir <data_dir>

    Override :data:`BILLY_DATA_DIR`

.. option:: --cache_dir <cache_dir>

    Override :data:`BILLY_CACHE_DIR`

.. option:: --error_dir <error_dir>

    Override :data:`BILLY_ERROR_DIR`

.. option:: --retries <retries>

    Override :data:`SCRAPELIB_RETRY_ATTEMPTS`

.. option:: --retry_wait <retry_wait>

    Override :data:`SCRAPELIB_RETRY_WAIT_SECONDS`
