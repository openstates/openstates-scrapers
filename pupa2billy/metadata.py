from utils import get_json


def make_metadata(abbr):
    j = get_json(abbr, 'jurisdiction')[0]

    # orgs = get_json(abbr, 'organization')
    # lower = None
    # upper = None
    # legislature = None
    # for org in orgs:
    #     if org['classification'] == 'legislature':
    #         legislature = org['name']
    #     elif org['classification'] == 'lower':
    #         lower = org['name']
    #     elif org['classification'] == 'upper':
    #         upper = org['name']

    session_details = {
        s['identifier']: {
            'type': s['classification'],
            'display_name': s['name'],
            '_scraped_name': s['identifier'],
            # TODO: start_date, end_date are missing
        }
        for s in j['legislative_sessions']
    }

    return {
        'name': j['name'],
        'abbreviation': abbr,
        'session_details': session_details,
    }
