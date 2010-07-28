from jsonschema.validator import JSONSchemaValidator
import datetime

from fiftystates.scrape import FiftystatesObject

class DatetimeValidator(JSONSchemaValidator):
    """ add a 'datetime' type to the valid types that verifies it recieves
        a datetime instance
    """
    def validate_type(self, x, fieldname, schema, fieldtype=None):
        if fieldtype == 'datetime':
            if not isinstance(x[fieldname], datetime.datetime):
                raise ValueError("Value for field '%s' is not a valid datetime"
                                 % fieldname)
            else:
                return x
        else:
            # convert FiftystatesObjects to dicts
            if isinstance(x[fieldname], FiftystatesObject):
                x[fieldname] = dict(x[fieldname])

            JSONSchemaValidator.validate_type(self, x, fieldname, schema,
                                              fieldtype)
