from jsonschema.validator import JSONSchemaValidator
import datetime

from fiftystates.scrape import FiftystatesObject

class DatetimeValidator(JSONSchemaValidator):
    """ add a 'datetime' type to the valid types that verifies it recieves
        a datetime instance
    """
    def __init__(self, *args, **kwargs):
        super(DatetimeValidator, self).__init__(*args, **kwargs)
        self._typesmap['datetime'] = lambda x: isinstance(x, datetime.datetime)
