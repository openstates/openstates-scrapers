# Open States Scrapers

This repository contains the code responsible for scraping bills & votes for Open States.

## Links

* [Contributor's Guide](https://docs.openstates.org/contributing/)
* [Documentation](https://docs.openstates.org/contributing/scrapers/)
* [Open States Issues](https://github.com/openstates/issues/issues)
* [Open States Discussions](https://github.com/openstates/issues/discussions)
* [Code of Conduct](https://docs.openstates.org/code-of-conduct/)

## Tests

A scraper change is checked by scraping: run the changed scraper before and after your change and include the difference in the PR. `pytest` (run from the repo root) covers only what a scrape can't:

* Code shared by more than one state, such as `scrapers/utils`. A change there can break states you didn't scrape.
* A pure function that turns text the state writes (a roll call line, PDF text, an action string, a date) into values. Add a few cases when you fix one.

Keep test inputs to short inline strings. Don't save whole pages, PDFs or API responses, don't build a scraper object or set its attributes, and don't test XPath or CSS selectors. When a site changes, a saved copy of the old page keeps passing, so a test of the markup doesn't protect anything.
