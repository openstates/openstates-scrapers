import json

from django.core.serializers.json import DateTimeAwareJSONEncoder
from piston.emitters import JSONEmitter


class OpenStateJSONEmitter(JSONEmitter):
    """
    Removes private fields (keys preceded by '_') recursively and
    outputs as JSON, with datetimes converted to strings.
    """

    def construct(self):
        return self._clean(super(OpenStateJSONEmitter, self).construct())

    def _clean(self, obj):
        if isinstance(obj, dict):
            # Expose the '_id' field as 'id' for certain object types
            if (obj.get('_type') in ('person',
                                     'committee',
                                     'event') and '_id' in obj):
                obj['id'] = obj['_id']

            for key, value in obj.items():
                if key.startswith('_'):
                    del obj[key]
                else:
                    obj[key] = self._clean(value)
        elif isinstance(obj, list):
            obj = [self._clean(item) for item in obj]
        elif hasattr(obj, '__dict__'):
            for key, value in obj.__dict__.items():
                if key.startswith('_'):
                    del obj.__dict__[key]
                else:
                    obj.__dict__[key] = self._clean(value)
        return obj

