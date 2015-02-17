import time
import scrapelib


class BackoffMixin(object):
    """
    Mixin for backing off tempermental websites
    """

    def urlopen(self, url, _backoff=None, **kwargs):
        _backoff = 0 if _backoff is None else _backoff
        time.sleep(_backoff * 5)
        try:
            response = super(BackoffMixin, self).urlopen(url)
        except scrapelib.HTTPError:
            _backoff = _backoff + 1
            if _backoff >= 5:
                raise
            self.warning("Bad HTTP response; attempt #{}".format(_backoff))
            return self.urlopen(url, _backoff=_backoff, **kwargs)
        return response
