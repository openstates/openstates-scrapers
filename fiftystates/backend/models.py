import datetime

from fiftystates.backend import conn

from mongokit import Document


def mongokit_register(cls):
    conn.register([cls])
    return cls


class FiftyStatesDocumentMetaClass(Document.__metaclass__):
    """
    Allow mongokit documents to inherit members of 'structure',
    'required_fields' and 'default_values'.
    """
    def __new__(cls, name, bases, attrs):
        new_cls = super(FiftyStatesDocumentMetaClass, cls).__new__(
            cls, name, bases, attrs)
        sup = super(cls, new_cls)

        if hasattr(new_cls, 'structure') and 'structure' in sup.__dict__:
            old_struct = new_cls.structure
            new_cls.structure = sup.__dict__['structure'].copy()
            new_cls.structure.update(old_struct)

        if (hasattr(new_cls, 'default_values') and
            'default_values' in sup.__dict__):

            old_defaults = new_cls.default_values
            new_cls.default_values = sup.__dict__['default_values'].copy()
            new_cls.default_values.update(old_defaults)

        if (hasattr(new_cls, 'required_fields') and
            'required_fields' in sup.__dict__):

            new_cls.required_fields.extend(sup.__dict__['required_fields'])

            # Remove duplicates
            new_cls.required_fields = list(set(new_cls.required_fields))

        return new_cls


class FiftyStatesDocument(Document):
    __metaclass__ = FiftyStatesDocumentMetaClass

    structure = {
        '_id': unicode,
        '_all_ids': list,
        '_type': unicode,
        'created_at': datetime.datetime,
        'updated_at': datetime.datetime,
        }

    required_fields = ['_type', 'created_at', 'updated_at']

    default_values = {'created_at': datetime.datetime.utcnow,
                      'updated_at': datetime.datetime.utcnow,
                      '_all_ids': []}

    use_dot_notation = True

    def save(self, *args, **kwargs):
        # Make uuid=False the default so that MongoKit doesn't override
        # our _id fields
        if 'uuid' not in kwargs:
            kwargs['uuid'] = False
        return super(FiftyStatesDocument, self).save(*args, **kwargs)


@mongokit_register
class Legislator(FiftyStatesDocument):
    structure = {
            'full_name': unicode,
            'first_name': unicode,
            'last_name': unicode,
            'middle_name': unicode,
            'votesmart_id': unicode,
            'nimsp_id': unicode,
            'roles': list,
            'created_at': datetime.datetime,
            'updated_at': datetime.datetime,
            }

    required_fields = ['full_name', 'first_name', 'last_name', 'middle_name',
                       'votesmart_id', 'nimsp_candidate_id']

    default_values = {'middle_name': u"",
                      'votesmart_id': None,
                      'nimsp_candidate_id': None}


@mongokit_register
class Bill(FiftyStatesDocument):
    structure = {
        'state': unicode,
        'session': unicode,
        'chamber': unicode,
        'title': unicode,
        'bill_id': unicode,
        'actions': list,
        'sponsors': list,
        'votes': list,
        }

    required_fields = ['state', 'session', 'chamber', 'title', 'bill_id',
                       'actions', 'sponsors', 'votes']

    default_values = {'_type': u"bill"}
