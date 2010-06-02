import datetime

from mongokit import Document


class FiftyStatesDocument(Document):
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


class Legislator(FiftyStatesDocument):
    structure = FiftyStatesDocument.structure.copy()
    structure.update({
            'full_name': unicode,
            'first_name': unicode,
            'last_name': unicode,
            'middle_name': unicode,
            'votesmart_id': unicode,
            'nimsp_id': unicode,
            'roles': list,
            'created_at': datetime.datetime,
            'updated_at': datetime.datetime,
            })

    required_fields = FiftyStatesDocument.required_fields[0:]
    required_fields.extend(
        ['full_name', 'first_name', 'last_name', 'middle_name'])

    default_values = FiftyStatesDocument.default_values.copy()
    default_values.update({
            '_type': u"person",
            'middle_name': u"",
            })


class Bill(FiftyStatesDocument):
    structure = FiftyStatesDocument.structure.copy()
    structure.update({
        'state': unicode,
        'session': unicode,
        'chamber': unicode,
        'title': unicode,
        'bill_id': unicode,
        'actions': list,
        'sponsors': list,
        'votes': list,
        })

    required_fields = FiftyStatesDocument.required_fields[0:]
    required_fields.extend(
        ['state', 'session', 'chamber', 'title', 'bill_id', 'actions',
         'sponsors', 'votes'])

    default_values = FiftyStatesDocument.default_values.copy()
    default_values.update({'_type': u"bill"})
