# Open States Scrapers

This repository contains the code responsible for scraping bills & votes for Open States.

## Links

* [Contributor's Guide](https://docs.openstates.org/en/latest/contributing/getting-started.html)
* [Documentation](https://docs.openstates.org/en/latest/contributing/scrapers.html)
* [Open States Discourse](https://discourse.openstates.org)


## State API Keys

A few states require credentials to access their APIs. If you want to run code for these states, get credentials for yourself using these steps:

* NY

  * Get credentials at: https://legislation.nysenate.gov/#signup
  * Set in environment prior to running scrape: ``NEW_YORK_API_KEY``

* IN

  * Get credentials at: http://docs.api.iga.in.gov/introduction.html#security-and-authentication
  * Set in environment prior to running scrape: ``INDIANA_API_KEY``
  * As a side note, Indiana also requires a `user-agent string <https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/User-Agent>`_, so set that in your environment as well, prior to running scrape: ``USER_AGENT``
