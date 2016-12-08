import requests


def get_with_increasing_timeout(scraper,link,fail=False,kwargs={}):
    #if fail is true, we want to throw an error if we can't
    #access the page we need
    #if it's false, throw a warning and keep going
    timeout_length = 2
    html = None
    while timeout_length < 65 and html is None:
        try:
            html = scraper.get(link,timeout=timeout_length,**kwargs)
        except (requests.exceptions.ConnectTimeout, requests.exceptions.ReadTimeout):
            old_length = timeout_length
            timeout_length **= 2 #this squares the result. awesome.
            scraper.logger.debug("Timed out after {now} seconds, increasing to {next} and trying again".format(now=old_length,next=timeout_length))
        else:
            return html
    if fail:
        raise AssertionError("Link failed after waiting over a minute, giving up and failing.")
    else:
        scraper.logger.warning("Link failed after waiting over a minute, giving up and moving on.")
