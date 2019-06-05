from openstates.utils.actions import Rule, BaseCategorizer


# These are regex patterns that map to action categories.
_categorizer_rules = (

    Rule((r'\(Ayes (?P<yes_votes>\d+)\.\s+Noes\s+'
          r'(?P<no_votes>\d+)\.( Page \S+\.)?\)')),

    Rule(r'^Introduced', 'introduction'),

    Rule(r'(?i)Referred to (?P<committees>.+)', 'referral-committee'),
    Rule(r'(?i)Referred to (?P<committees>.+?)(\.\s+suspense)',
         'referral-committee'),
    Rule(r're-refer to Standing (?P<committees>[^.]+)\.',
         'referral-committee'),

    Rule(r'Read first time\.', 'reading-1'),
    Rule(r'Read second time and amended',
         ['reading-2']),
    Rule(r'Read third time', 'reading-3'),
    Rule(r'Read third time. Refused passage\.',
         'failure'),
    Rule([r'(?i)read third time.{,5}passed',
          r'(?i)Read third time.+?Passed'],
         ['passage', 'reading-3']),

    Rule(r'Approved by the Governor', 'executive-signature'),
    Rule(r'Approved by the Governor with item veto',
         'executive-veto-line-item'),
    Rule('Vetoed by Governor', 'executive-veto'),
    Rule('Vetoed by the Governor', 'executive-veto'),
    Rule(r'To Governor', 'executive-receipt'),

    Rule(r'amendments concurred in', 'amendment-passage'),
    Rule(r'refused to concur in Assembly amendments', 'amendment-failure'),

    Rule(r'Failed passage in committee', 'committee-failure'),
    Rule(r'(?i)From committee: ((?!Without further action))', 'committee-passage'),
    Rule(r'(?i)From committee: Do pass', 'committee-passage-favorable'),
    Rule(r'From committee with author\'s amendments', 'committee-passage'),

    # Resolutions
    Rule(r'Adopted', 'passage'),
    Rule(r'Read', 'reading-1'),
    Rule(r'^From committee: Be adopted', 'committee-passage-favorable'),
)


class CACategorizer(BaseCategorizer):
    rules = _categorizer_rules
