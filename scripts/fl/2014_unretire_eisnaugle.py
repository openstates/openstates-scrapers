from billy.core import db


def main():
    eisnaugle = db.legislators.find_one('FLL000075')

    # Make him active.
    eisnaugle['active'] = True

    # Hack his current roles.
    eisnaugle['roles'].insert(0, {
        "term": "2013-2014",
        "end_date": None,
        "district": "44",
        "chamber": "lower",
        "state": "fl",
        "party": "Republican",
        "type": "member",
        "start_date": None
    })

    # Save this hotness
    db.legislators.save(eisnaugle)


if __name__ == '__main__':
    main()