def get_slug_for_session(session):
    # Session-slugs in the Arkansas LIS are the four-digit year, plus:
    # `R` for regular session
    # `S#` for special session, plus ordinal
    # `F` for fiscal session (these are common in even-numbered years)

    # In our `__init__.py` session metadata, we don't put an `R`
    # after our regular-session identifiers, so need to add one here
    if "S" in session or session.endswith("F"):
        return session
    else:
        return "{}R".format(session)
