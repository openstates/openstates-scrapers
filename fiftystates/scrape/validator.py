from jsonschema.validator import JSONSchemaValidator
import datetime

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
            JSONSchemaValidator.validate_type(self, x, fieldname, schema,
                                              fieldtype)
