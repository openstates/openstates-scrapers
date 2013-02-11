'''HTML entity defs weren't getting unescaped during import until
today. This script retroactively fixes the ones in the feeds_db.
'''
import re, htmlentitydefs

from billy.core import feeds_db


def unescape(text):
    '''Removes HTML or XML character references and entities from a text string.
    @param text The HTML (or XML) source text.
    @return The plain text, as a Unicode string, if necessary.
    from
    '''
    def fixup(m):
        text = m.group(0)
        if text[:2] == "&#":
            # character reference
            try:
                if text[:3] == "&#x":
                    return unichr(int(text[3:-1], 16))
                else:
                    return unichr(int(text[2:-1]))
            except ValueError:
                pass
        else:
            # named entity
            try:
                text = unichr(htmlentitydefs.name2codepoint[text[1:-1]])
            except KeyError:
                pass
        return text  # leave as is
    return re.sub("&#?\w+;", fixup, text)


def main():
    for entry in feeds_db.entries.find():
        entry['title'] = unescape(entry['title'])
        feeds_db.entries.save(entry)


if __name__ == '__main__':
    main()
