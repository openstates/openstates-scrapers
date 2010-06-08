status = dict(
    bills=True,
    bill_versions=True,
    sponsors=True,
    actions=True,
    votes=True,
    legislators=True,
    contributors=['Michael Stephens'],
    notes="",
    )

metadata = dict(
    name='Pennsylvania',
    legislature_name='Pennsylvania General Assembly',
    upper_chamber_name='Senate',
    lower_chamber_name='House of Representatives',
    upper_chamber_title='Senator',
    lower_chamber_title='Representative',
    upper_chamber_term=4,
    lower_chamber_term=2,
    sessions=[
        dict(name='2009-2010', sub_sessions=[
                '2009-2010 Special Session #1 (Transportation)'],
             start_year=2009, end_year=2010)],
    )
