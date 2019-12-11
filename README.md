# Open States Scrapers

This repository contains the code responsible for scraping bills & votes for Open States.

## Links

* [Open States API](https://docs.openstates.org/en/latest/api/index.html)
* [Open States Discourse](https://discourse.openstates.org)


## Contributing

If you're interested in contributing, please visit [Our Getting Started Guide](https://docs.openstates.org/en/latest/contributing/getting-started.html#start-contributing-to-open-states).


## A Note About Testing

Our scraping framework, pupa, has a strong test harness, and requires well-structured data when ingesting. Furthermore, Open States scrapers should be written to fail when they encounter unexpected data, rather than guessing at its format and possibly ingesting bad data. Together, this means that there aren't many benefits to writing unit tests for particular Open States scrapers, versus high upkeep costs.

Occasionally, states *will* have unit tests, though, for specific structural cases. To run all tests::

  docker-compose run --rm --entrypoint=nosetests scrape /srv/openstates-web/openstates


## State API Keys

A few states require credentials to access their APIs. If you want to run code for these states, get credentials for yourself using these steps:

* NY

  * Get credentials at: https://legislation.nysenate.gov/#signup
  * Set in environment prior to running scrape: ``NEW_YORK_API_KEY``

* IN

  * Get credentials at: http://docs.api.iga.in.gov/introduction.html#security-and-authentication
  * Set in environment prior to running scrape: ``INDIANA_API_KEY``
  * As a side note, Indiana also requires a `user-agent string <https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/User-Agent>`_, so set that in your environment as well, prior to running scrape: ``USER_AGENT``
