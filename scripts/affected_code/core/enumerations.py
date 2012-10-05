enums = ['paragraph', 'division', 'chapter', 'section', 'clause',
         'article', 'part', 'rule']
enums += ['sub' + s for s in enums]

regex = r'(%s)' % '|'.join(sorted(enums, key=len, reverse=True))
