categories = [
    ('bill:introduced',
     'Bill is introduced or prefiled'),

    ('bill:passed',
     'Bill has passed a chamber'),

    ('bill:failed',
     'Bill has failed to pass a chamber'),

    ('bill:withdrawn',
     'Bill has been withdrawn from consideration'),

    ('bill:veto_override:passed',
     'The chamber attempted a veto override and succeeded'),

    ('bill:veto_override:failed',
     'The chamber attempted a veto override and failed'),

    ('bill:reading:1',
     'A bill has undergone its first reading'),

    ('bill:reading:2',
     'A bill has undergone its second reading'),

    ('bill:reading:3',
     'A bill has undergone its third (or final) reading'),

    ('bill:filed',
     ('A bill has been filed (for states where this is '
      'a separate event from bill:introduced')),

    ('bill:substituted',
     ('A bill has been replaced with a substituted wholesale '
      '(called hoghousing in some states')),

    ('governor:received',
     'The bill has been transmitted to the governor for consideration'),

    ('governor:signed',
     'The bill has signed into law by the governor'),

    ('governor:vetoed',
     'The bill has been vetoed by the governor'),

    ('governor:vetoed:line-item',
     'The governor has issued a line-item (partial) veto'),

    ('amendment:introduced',
     'An amendment has been offered on the bill'),

    ('amendment:passed',
     'The bill has been amended'),

    ('amendment:failed',
     'An offered amendment has failed'),

    ('amendment:amended',
     'An offered amendment has been amended (seen in Texas)'),

    ('amendment:withdrawn',
     'An offered amendment has been withdrawn'),

    ('amendment:tabled',
     ('An amendment has been \'laid on the table\' '
      '(generally preventing further consideration)')),

    ('committee:referred',
     'The bill has been referred to a committee'),

    ('committee:passed',
     'The bill has been passed out of a committee'),

    ('committee:passed:favorable',
     'The bill has been passed out of a committee with a favorable report'),

    ('committee:passed:unfavorable',
     'The bill has been passed out of a committee with an unfavorable report'),

    ('committee:failed',
     'The bill has failed to make it out of committee other'),
    ]
