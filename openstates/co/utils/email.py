def mailto_to_email(mailto_url):
    """Return a single email extracted from 'mailto:name@domain.com'"""
    email = mailto_url.lstrip('mailto:')
    return email
