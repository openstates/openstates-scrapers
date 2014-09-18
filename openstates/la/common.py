from billy.scrape import Scraper
import requests


class BackoffScraper(Scraper):
    _backoff_count = 0
    def urlopen(self, *args, **kwargs):
        # I miss you, kwonly args.
        if self._backoff_count >= 10:
            raise
        try:
            x = Scraper.urlopen(self, *args, **kwargs)
            self._backoff_count = 0
            return x
        except requests.exceptions.Timeout:
            self._backoff_count += 1
            return self.urlopen(*args, **kwargs)
