from openstates.scrape import Scraper

# legis.iowa.gov sometimes answers 200 with a JS bot-check page and no data.
# It's transient, so a plain retry gets the real page.
_BOT_CHECK_MARKER = b"eval(function(p,a,c,k,e,d)"


def is_bot_check(response):
    return _BOT_CHECK_MARKER in response.content[:500]


class IAScraper(Scraper):
    # scrapelib retries a rejected response with backoff, then raises HTTPError
    def accept_response(self, response, **kwargs):
        return super().accept_response(response) and not is_bot_check(response)

    def should_cache_response(self, response):
        return super().should_cache_response(response) and not is_bot_check(response)
