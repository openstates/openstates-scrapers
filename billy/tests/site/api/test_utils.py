from billy.site.api import utils

def test_district_from_census_name():
    tests = [
        (('vt', 'lower', 'Washington-5 State House District'),
         'Washington-5'),
        (('ca', 'lower', 'Assembly District 6'), '6'),
        (('mn', 'lower', 'State House District 9A'), '09A'),
        (('nv', 'uper', 'State Senatorial District 7'), '7'),
        (('vt', 'lower', 'Orleans-Franklin-1 State House District'),
         'Orleans-Franklin-1'),
        (('nv', 'upper', 'Capital Senatorial District'),
         'Capital Senatorial District'),
        (('nv', 'upper', 'Central Nevada Senatorial District'),
         'Central Nevada Senatorial District'),
        (('vt', 'upper', 'Rutland State Senate District'),
         'Rutland'),
        (('ex', 'lower', 'Senate District 8B'), '8B')]

    for census, ours in tests:
        assert utils.district_from_census_name(*census) == ours
