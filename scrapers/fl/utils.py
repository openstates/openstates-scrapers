import logging
import random
import time
from http.client import RemoteDisconnected
from urllib.error import URLError

from requests.exceptions import ConnectionError, Timeout, RequestException

logger = logging.getLogger(__name__)


def fix_name(name):
    # handles cases like Watson, Jr., Clovis
    if ", " not in name:
        return name
    last, first = name.rsplit(", ", 1)
    return first + " " + last


def get_random_user_agent():
    """
    Return a random user agent to help avoid detection.
    """
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1",
        "Mozilla/5.0 (iPad; CPU OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36 Edg/91.0.864.59",
    ]
    return random.choice(user_agents)


def retry_on_connection_error(func, max_retries=5, initial_backoff=2, max_backoff=60):
    """
    Retry a function call on connection errors with exponential backoff.

    Args:
        func: Function to call
        max_retries: Maximum number of retries
        initial_backoff: Initial backoff time in seconds
        max_backoff: Maximum backoff time in seconds

    Returns:
        The result of the function call
    """
    retries = 0
    backoff = initial_backoff

    while True:
        try:
            return func()
        except (
            ConnectionError,
            RemoteDisconnected,
            URLError,
            Timeout,
            RequestException,
        ) as e:
            # a 4xx won't change on retry
            status = getattr(getattr(e, "response", None), "status_code", None)
            if status and 400 <= status < 500 and status not in (403, 429):
                raise
            retries += 1
            if retries > max_retries:
                logger.error(f"Max retries ({max_retries}) exceeded. Last error: {e}")
                raise

            # Calculate backoff with jitter
            jitter = random.uniform(0.8, 1.2)
            current_backoff = min(backoff * jitter, max_backoff)

            logger.warning(
                f"Connection error: {e}. Retrying in {current_backoff:.2f} seconds (attempt {retries}/{max_retries})"
            )
            time.sleep(current_backoff)

            # Increase backoff for next retry
            backoff = min(backoff * 2, max_backoff)

            # Rotate user agent for next attempt
            if hasattr(func, "__self__") and hasattr(func.__self__, "headers"):
                func.__self__.headers.update({"User-Agent": get_random_user_agent()})
