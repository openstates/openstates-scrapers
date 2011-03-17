#!/usr/bin/env python
# encoding: utf-8
"""
Common data and functions for scraping.
"""

STATE_URL = "http://www.capitol.hawaii.gov"
chamber_label = {'upper': 'SB', 'lower': 'HB'}
house = {'H':'lower', 'S':'upper', 'D': 'Data Systems',
    '$':  'Appropriation measure', 'ConAm': 'Constitutional Amendment',}

def get_session_details(session):
    """Returns year (as string) and session type from session title.
    See module __init__.py for session titles.
    """
    words = session.lower().split()
    session_type = ''
    if 'special' in words:
        session_type = 'special'
    elif 'regular' in words:
        session_type = 'regular'
    return words[0], session_type
    
def substitution_count(text):
    """Returns a count of substitutions in the text string."""
    return text.count('%s')
    
def get_chamber_string(url, chamber):
    """Returns the chamber substitution string required by url"""
    if substitution_count(url) == 1:
        chamber_string = ''
    else:
        chamber_string = chamber_label[chamber]
    return chamber_string


