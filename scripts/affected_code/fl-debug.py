import re
import webbrowser
import collections

import lxml.html
import logbook

from core.utils import parse, get_billtext
from core.fl import Lexer, Parser


logger = logbook.Logger('fl-debug')
Section = collections.namedtuple('Section', 'enum content')


def extract_sections(text):
    doc = lxml.html.fromstring(text)
    text = '\n'.join(n.text_content() for n in doc.xpath('//td[2]'))
    text = text.replace(u'\xa0', ' ')
    # Note, currently skips last section (usually effective date).
    matches = re.finditer('     Section (\d\w*)\.\s+(.+?)(?:\n     )', text, re.S)
    for m in matches:
        enum = m.group(1)
        content = re.sub(r'\s+', ' ', m.group(2))
        yield Section(enum, content)


def main():
    for filename, text in get_billtext('fl'):
        logger.info('extracting sections: %r' % filename)
        # webbrowser.open('file:///%s' % filename)
        for section in extract_sections(text):
            section_text = section.content
            print section_text
            if 'repeal' in section_text.lower() or 'add' in section_text.lower():
                # import pdb;pdb.set_trace()
                tokens = parse(Lexer, Parser, None, section_text)
                import pdb;pdb.set_trace()


if __name__ == '__main__':
    main()
