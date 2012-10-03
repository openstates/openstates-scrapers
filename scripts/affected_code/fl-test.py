s = '''
Subsections (1), (2), (3), (4), and (6) and paragraph (c) of subsection (7) of section 1002.69, Florida Statutes, are amended to read:
Section 1003.46, Florida Statutes, is amended to read:
Paragraph (d) of subsection (3) of section 1002.20, Florida Statutes, is amended to read:
Subsection (10) of section 447.203, Florida Statutes, is amended to read:
Paragraph (a) of subsection (4) of section 1001.20, Florida Statutes, is amended to read:
Paragraphs (b) and (e) of subsection (1) and subsections (2) and (4) of section 1006.33, Florida Statutes, are amended to read:
Subsection (1), paragraph (a) of subsection (2), and paragraphs (b) and (e) of subsection (3) of section 1006.28, Florida Statutes, are amended to read:
Subsections (1), (2), (3), and (7) of section 1006.34, Florida Statutes, are amended to read:
Subsection (2), paragraph (a) of subsection (3), and subsection (4) of section 1006.40, Florida Statutes, are amended to read:
Paragraph (p) of subsection (1) and paragraph (b) of subsection (6) of section 1011.62, Florida Statutes, are amended to read:
Paragraph (b) of subsection (3) and subsection (4) of section 1008.33, Florida Statutes, are amended to read:

Subsection (23) of section 1001.42, Florida Statutes, is amended to read:
Paragraph (b) of subsection (5) of section 1002.33, Florida Statutes, is amended to read:
Paragraph (a) of subsection (1) of section 1002.37, Florida Statutes, is amended to read:
Paragraph (f) is added to subsection (3) of section 1002.38, Florida Statutes, to read:
Paragraph (b) of subsection (2) of section 1002.45, Florida Statutes, is amended to read:
Subsection (1) and paragraph (c) of subsection (3) of section 1002.67, Florida Statutes, are amended to read:
Subsection (2) of section 1002.73, Florida Statutes, is amended to read:
Paragraph (c) of subsection (4) of section 1003.03, Florida Statutes, is amended to read:
Subsection (1) of section 1003.4156, Florida Statutes, is amended to read:
Section 1003.4203, Florida Statutes, is created to read:
Subsection (2) of section 1003.428, Florida Statutes, is amended to read:
Subsection (1) of section 1003.492, Florida Statutes, is amended to read:
Section 1003.493, Florida Statutes, is amended to read:
Section 1003.575, Florida Statutes, is amended to read:
Subsection (2) of section 1003.621, Florida Statutes, is amended to read:
Section 1006.29, Florida Statutes, is amended to read:
Section 1006.30, Florida Statutes, is amended to read:
Section 1006.31, Florida Statutes, is amended to read:
Section 1006.32, Florida Statutes, is amended to read:
Subsection (2) of section 1006.35, Florida Statutes, is amended to read:
Section 1006.36, Florida Statutes, is amended to read:
Section 1006.37, Florida Statutes, is repealed.
Subsection (5) of section 1006.39, Florida Statutes, is amended to read:
Section 1006.43, Florida Statutes, is amended to read:
Effective upon this act becoming a law, subsection (2) and paragraph (c) of subsection (3) of section 1008.22, Florida Statutes, are amended to read:
Subsection (3) of section 1008.34, Florida Statutes, is amended to read:
Paragraph (a) of subsection (3) of section 1011.01, Florida Statutes, is amended to read:
Subsection (4) of section 1011.03, Florida Statutes, is amended to read:
Subsection (1) of section 1011.61, Florida Statutes, is amended to read:
Subsection (1) of section 1012.39, Florida Statutes, is amended to read:'''


def main():
    from core.utils import parse
    from core.fl import Lexer, Parser
    for section in filter(None, s.splitlines()):
        tokens = parse(Lexer, Parser, None, section)
        print section

if __name__ == '__main__':
    main()