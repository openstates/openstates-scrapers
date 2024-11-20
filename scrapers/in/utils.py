import requests
import logging
import time

logging.getLogger("IN").setLevel(logging.WARNING)
log = logging.getLogger("openstates")


def get_with_increasing_timeout(scraper, link, fail=False, kwargs={}):
    # if fail is true, we want to throw an error if we can't
    # access the page we need
    # if it's false, throw a warning and keep going
    timeout_length = 8
    html = None
    while timeout_length < 65 and html is None:
        try:
            html = scraper.get(link, timeout=timeout_length, **kwargs)
        except (requests.exceptions.ConnectTimeout, requests.exceptions.ReadTimeout):
            old_length = timeout_length
            timeout_length *= 2
            scraper.logger.debug(
                "Timed out after {now} seconds, "
                "increasing to {next} and trying again".format(
                    now=old_length, next=timeout_length
                )
            )
        else:
            return html
    if fail:
        raise AssertionError(
            "Link failed after waiting over a minute, giving up and failing."
        )
    else:
        scraper.logger.warning(
            "Link failed after waiting over a minute, giving up and moving on."
        )


def add_space(text):
    """
    Add a space between the bill number and the bill name

    Parameters
    ----------
    text : str
        The bill number and name, e.g. HB 1001

    Examples
    --------
    >>> add_space("HB1001")
    """
    index = 0
    for i, char in enumerate(text):
        if not char.isalpha():
            index = i
            break

    # Slice the string to get the number and text parts
    alpha = text[:index]
    number = text[index:].lstrip("0")

    new_string = f"{alpha} {number}"

    return new_string


def backoff(function, *args, **kwargs):
    retries = 5

    def _():
        time.sleep(1)
        return function(*args, **kwargs)

    for attempt in range(retries):
        try:
            return _()
        except Exception as e:
            backoff = (attempt + 1) * 15
            log.warning(
                "[attempt %s]: %s. Backing off for %s seconds."
                % (attempt, str(e), backoff)
            )
            time.sleep(backoff)

    raise Exception("INDIANA API returns still None. Please confirm API status.")
