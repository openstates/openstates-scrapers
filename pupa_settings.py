from openstates import transformers

IMPORT_TRANSFORMERS = {
    'bill': {
        'identifier': transformers.fix_bill_id,
    }
}


print('loaded Open States pupa settings...')
