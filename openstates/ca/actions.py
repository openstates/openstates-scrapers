from billy.scrape.actions import Rule, BaseCategorizer


# These are regex patterns that map to action categories.
_categorizer_rules = (

    Rule((r'\(Ayes (?P<yes_votes>\d+)\.\s+Noes\s+'
          r'(?P<no_votes>\d+)\.( Page \S+\.)?\)')),

    Rule(r'^Introduced', 'bill:introduced'),

    Rule(r'(?i)Referred to (?P<committees>.+)', 'committee:referred'),
    Rule(r'(?i)Referred to (?P<committees>.+?)(\.\s+suspense)',
         'committee:referred'),
    Rule(r're-refer to Standing (?P<committees>[^.]+)\.',
         'committee:referred'),

    Rule(r'Read first time\.', 'bill:reading:1'),
    Rule(r'Read second time and amended',
          ['bill:reading:2']),
    Rule(r'Read third time', 'bill:reading:3'),
    Rule(r'Read third time. Refused passage\.',
         'bill:failed'),
    Rule([r'(?i)read third time.{,5}passed',
          r'(?i)Read third time.+?Passed'],
         ['bill:passed', 'bill:reading:3']),

    Rule(r'Approved by the Governor', 'governor:signed'),
    Rule(r'Approved by the Governor with item veto',
         'governor:vetoed:line-item'),
    Rule('Vetoed by Governor', 'governor:vetoed'),
    Rule('Vetoed by the Governor','governor:vetoed'),
    Rule(r'To Governor', 'governor:received'),

    Rule(r'amendments concurred in', 'amendment:passed'),
    Rule(r'refused to concur in Assembly amendments', 'amendment:failed'),

    Rule(r'Failed passage in committee', 'committee:failed'),
    Rule(r'(?i)From committee', 'committee:passed'),
    Rule(r'(?i)From committee: Do pass', 'committee:passed:favorable'),
    Rule(r'From committee with author\'s amendments', 'committee:passed'),

    # Resolutions
    Rule(r'Adopted', 'bill:passed'),
    Rule(r'Read', 'bill:reading:1'),
    Rule(r'^From committee: Be adopted', 'committee:passed:favorable'),
    )


class CACategorizer(BaseCategorizer):
    rules = _categorizer_rules
