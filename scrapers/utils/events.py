import datetime
import itertools
import operator

from dateutil.relativedelta import relativedelta
from openstates.scrape import Event
from typing import Dict


# the current function to set coordinates requires a
# valid URL and Note, which we often don't have.
# so this will add just coordinates
def set_coordinates(event: Event, lat, lon):
    # the schema requires strings for these
    coords = {
        "latitude": str(lat),
        "longitude": str(lon),
    }
    loc_dict = event.location
    loc_dict["coordinates"] = coords
    event.__setattr__("location", loc_dict)


def set_location_url(event: Event, url: str):
    loc_dict = event.location
    loc_dict["url"] = url
    event.__setattr__("location", loc_dict)


# loop through a dict of
# {"location string", (lat, lon)} entries
# and update the location lat/lon if any matches are found
def match_coordinates(event: Event, locations: Dict[str, tuple]):
    for location, coords in locations.items():
        if location.lower() in event.location.get("name").lower():
            set_coordinates(event, coords[0], coords[1])
            return


def month_range(
    start: datetime.date,
    end: datetime.date,
):
    """Yields the 1st day of each month in the given date range."""
    yield from itertools.takewhile(
        lambda date: date < end,
        itertools.accumulate(
            itertools.repeat(relativedelta(months=1)),
            operator.add,
            initial=start,
        ),
    )
