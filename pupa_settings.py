from openstates import transformers

ENABLE_PEOPLE_AND_ORGS = False
ENABLE_EVENTS = False

IMPORT_TRANSFORMERS = {
    'bill': {
        'identifier': transformers.fix_bill_id,
    }
}


print('loaded Open States pupa settings...')
