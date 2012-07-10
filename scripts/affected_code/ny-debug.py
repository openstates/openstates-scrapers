import os
import re
import pprint
from functools import partial
from os.path import join

from utils import parse
from ny import Lexer, Parser, ParserState


DATA = '/home/thom/data/ny_billtext/data'


def extract_sections(text):

    # Slice beginning crap.
    _, text = text.split('DO ENACT AS FOLLOWS:')

    # Kill line numbers.
    text = re.sub(r' {3,4}\d+ {2}', '', text)

    paragraphs = []
    text = iter(text.splitlines())
    lines = []
    while True:
        try:
            line = next(text)
        except StopIteration:
            paragraphs.append(' '.join(lines))
            break

        lines.append(line)
        if len(line) != 72:
            paragraphs.append(' '.join(lines))
            lines = []

    def filterfunc(s):
        return (not (s.isupper() or ('shall take effect' in s)) \
                and (re.search(r'^  Section +1.', s) or \
                     re.search(r'^  S {1,2}\d+', s)))

    paragraphs = filter(filterfunc, paragraphs)
    paragraphs = map(partial(re.sub, r'\s+', ' '), paragraphs)

    return paragraphs


def main():
    for filename in os.listdir(DATA):
        filename = join(DATA, filename)
        with open(filename) as f:
            text = f.read()
            sections = extract_sections(text)
            for s in sections:
                print s
                parsed = parse(Lexer, Parser, ParserState, s)
                print s
                print filename
                pprint.pprint(parsed)
            import pdb;pdb.set_trace()


if __name__ == '__main__':
    main()
