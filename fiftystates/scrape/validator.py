from validictory.validator import SchemaValidator
import datetime

from fiftystates.scrape import FiftystatesObject

class DatetimeValidator(SchemaValidator):
    """ add a 'datetime' type to the valid types that verifies it recieves
        a datetime instance
    """

    def validate_type_datetime(self, x):
        return isinstance(x, datetime.datetime)
