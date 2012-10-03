import unittest
import pprint

from ny import Lexer, Parser, ParserState
from utils import parse


class TestRelatedCitation(unittest.TestCase):

    maxDiff = None

    def test_parse_all(self):
        for string, data in samples:
            _data = parse(Lexer, Parser, ParserState, string)
            import pdb;pdb.set_trace()
            # pprint.pprint(data)
            # pprint.pprint(_data)
            #self.assertEqual(data, _data)


samples = [

    ('Section 32 of the labor law is amended to read as follows:',
        {
            'type': 'statute',
            'id': 'labor law',
            'paths': [
                [{'type': 'section', 'id': '32'}]
                ],
            'impact': 'amended'
        }
    ),

    (('Section 191-b of the labor law, as added by chapter 451 of '
      'the laws of 1987, is amended to read as follows:'),
        {
            'type': 'statute',
            'id': 'labor law',
            'paths': [
                [{'type': 'section', 'id': '191-b'}]
                ],
            'impact': 'amended'
        }
    ),

    (('Subdivision 1 of section 100 of the labor law, as amended '
      'by chapter 757 of the laws of 1975, is amended to read as follows:'),
        {
            'type': 'statute',
            'id': 'labor law',
            'paths': [
                [{'type': 'subdivision', 'id': '1'},
                 {'type': 'section', 'id': '100'}]
                ],
            'impact': 'amended'
        }
    ),

    (('Subdivision 1 of section 21 of the labor law, added by section '
      '146 of part B of chapter 436 of the laws of 1997 and renumbered by '
      'chapter 214 of the laws of 1998, is amended to read as follows:'),
        {
            'type': 'statute',
            'id': 'labor law',
            'paths': [
                [{'type': 'subdivision', 'id': '1'},
                 {'type': 'section', 'id': '21'}]
                ],
            'impact': 'amended'
        }
    ),

    (('Section 57-0131 of the environmental conservation law, as amended '
      'by chapter 286 of the laws of 1998, is amended to read as follows:'),
        {
            'type': 'statute',
            'id': 'environmental conservation law',
            'paths': [[{'type': 'section', 'id': '57-0131'}]],
            'impact': 'amended'
        }
    ),

    (('Subdivision 4 of section 30 of the labor law, as amended by '
      'chapter 756 of the laws of 1975 and renumbered by chapter 162 '
      'of the laws of 1993, is amended to read as follows:'),
        {
            'id': 'labor law',
            'type': 'statute',
            'paths': [
                [{'type': 'subdivision', 'id': '4'},
                 {'type': 'section', 'id': '30'}]
                ],
            'impact': 'amended'
        }
    ),

    ('Section 30 of the labor law is renumbered section 60.',
        {
            'id': 'labor law',
            'type': 'statute',
            'paths': [
                [{'type': 'section', 'id': '30'}]
                ],
            'impact': 'renumbered',
            'details': [
                [{'type': 'section', 'id': '60'}]
                ]
        }
    ),

    (('Subdivision 1 of section 20 of chapter 784 of the laws of 1951, '
      'constituting the New York state defense emergency act, is '
      'amended to read as follows:'),
      {
          'act_name': 'New York state defense emergency act',
          'impact': 'amended',
          'paths': [
                [{'id': '1', 'type': 'subdivision'},
                 {'id': '20', 'type': 'section'},
                 {'id': '784', 'type': 'chapter'}]
                ],
         'type': 'session_law',
         'year': '1951'}
    ),

    (('Subdivision 1 of section 20 of chapter 784 of the laws of '
      '1951, constituting the New York state defense emergency act, '
      'as amended by chapter 3 of the laws of 1961, is amended to '
      'read as follows:'),
        {
            'year': '1951',
            'type': 'session_law',
            'paths': [
                [{'type': 'subdivision', 'id': '1'},
                 {'type': 'section', 'id': '20'},
                 {'id': '784', 'type': 'chapter'}],
                ],
            'act_name': 'New York state defense emergency act',
            'impact': 'amended',
        }
    ),

    (('Section 4 of chapter 694 of the laws of 1962, relating to the '
      'transfer of judges to the civil court of the city of New York, '
      'is amended to read as follows:'),
        {
            'year': '1962',
            'type': 'session_law',
            'paths': [
                [{'type': 'section', 'id': '4'},
                 {'type': 'chapter', 'id': '694'}],
                ],
            'impact': 'amended',
        }
    ),

    (('Section 4502 of the public health law, as added by a chapter '
      'of the laws of 1989, amending the public health law relating '
      'to health foods, as proposed in legislative bill number S. '
      '3601, is amended to read as follows:'),
        {
            'id': 'public health law',
            'type': 'statute',
            'paths': [
                [{'type': 'section', 'id': '4502'}]
                ],
            'impact': 'amended',
        }
    ),

    (('Section 4508 of the public health law, as added by a chapter '
      'of the laws of 1989, amending the public health law relating '
      'to health foods, as proposed in legislative bill number S. 3601, '
      'is amended to read as follows:'),
        {
            'id': 'public health law',
            'type': 'statute',
            'paths': [
                [{'type': 'section', 'id': '4508'}]
                ],
            'impact': 'amended',
        }
    ),

    (('Section 3 of a chapter 234 of the laws of 1989, amending the public '
      'health law relating to the sale of health foods, as proposed in '
      'legislative bill number A. 5730, is amended to read as follows:'),
        {
            'year': '1989',
            'type': 'session_law',
            'paths': [
                [{'type': 'section', 'id': '3'},
                 {'type': 'chapter', 'id': '234'}]
                ],
            'impact': 'amended',
        }
    ),

    (('Section 4 of a chapter 234 of the laws of 1989, amended the public '
      'health law relating to the sale of health foods, as proposed in '
      'legislative bill number A. 5730, is amended to read as follows:'),
        {
            'year': '1989',
            'type': 'session_law',
            'paths': [
                [{'type': 'section', 'id': '4'},
                 {'type': 'chapter', 'id': '234'}]
                ],
            'impact': 'amended',
        }
    ),

    (('Section 401 of the education law, as amended by a chapter of '
      'the laws of 1989, entitled "AN ACT to amend the civil rights '
      'law, the education law, the executive law and the general '
      'municipal law, in relation to prohibiting discrimination in '
      'employment of physically handicapped persons, making certain '
      'confirming amendments therein and making an appropriation '
      'therefor", is amended to read as follows:'),
        {
            'id': 'education law',
            'type': 'statute',
            'paths': [
                [{'type': 'section', 'id': '401'}]
                ],
            'impact': 'amended',
        }
    ),

    (('Sections 16-a and 18-a of the general construction law, as added '
      'by chapter 917 of the laws of 1920, are amended to read as follows:'),
        {
            'id': 'general construction law',
            'type': 'statute',
            'paths': [
                [{'type': 'section', 'id': '16-a'}],
                [{'type': 'section', 'id': '18-a'}]
                ],
            'impact': 'amended',
        }
    ),

    #
    (('Section 631 of the tax law, as amended by chapter 28 of the laws '
      'of 1987, subsection (a) as amended by chapter 170 of the laws of '
      '1994, subparagraph (c) of paragraph 1 of subsection (b) and '
      'paragraph 2 of subsection (b) as amended, subparagraph (D) of '
      'paragraph 1 of subsection (b) as added by chapter 586 of the laws '
      'of 1999, and paragraph 4 of subsection (b) as amended by chapter '
      '760 of the laws of 1992, is amended to read as follows:'),
        {
            'id': 'tax law',
            'type': 'statute',
            'paths': [
                [{'type': 'section', 'id': '631'}],
                ],
            'impact': 'amended',
        }
    ),


    (('Paragraphs (d) and (f) of section 1513-a of the not-for-profit '
      'corporation law, as added by chapter 478 of the laws of 2003, are '
      'amended and four new paragraphs (i), (j), (k) and (l) are added to '
      'read as follows:'),
        {
            'id': 'not-for-profit corporation law',
            'type': 'statute',
            'paths': [
                [{'type': 'section', 'id': '1513-a'},
                 {'type': 'paragraph', 'id': '(d)'}],
                [{'type': 'section', 'id': '1513-a'},
                 {'type': 'paragraph', 'id': '(f)'}],
                ],
            'impact': 'amended',
            'details': [
                [{'type': 'section', 'id': '1513-a'},
                 {'type': 'paragraph', 'id': '(i)'}],
                [{'type': 'section', 'id': '1513-a'},
                 {'type': 'paragraph', 'id': '(j)'}],
                [{'type': 'section', 'id': '1513-a'},
                 {'type': 'paragraph', 'id': '(k)'}],
                [{'type': 'section', 'id': '1513-a'},
                 {'type': 'paragraph', 'id': '(l)'}],
                ],
        }
    ),

    # Aaaaaaand then there are these two monsters. Let's not worry about them...

    (('Section 27-1018 of the administrative code of the city of New '
      'York, subdivisions c, d and e as added by local law number 61 of '
      'the city of New York for the year 1987, is amended to read as '
      'follows:'),
        {
            'id': 'administrative code of the city of New York',
            'type': 'statute',
            'paths': [
                [{'type': 'section', 'id': '27-1018'}],
                ],
            'impact': 'amended'
        }
    ),

    (('Paragraph 2, subparagraph (A) of paragraph 4, and paragraph 6 of '
      'subsection (b) of section 92-85 of the codes and ordinances of the '
      'city of Yonkers, paragraph 2 and subparagraph (A) of paragraph 4 '
      'as added by local law number 8 and paragraph 6 as amended by local '
      'law number 9 of the city of Yonkers for the year 1984, are amended '
      'to read as follows:'),
        {
            'type': 'statute',
            'id': 'codes and ordinances of the city of Yonkers',
            'paths': [[{'type': 'paragraph', 'id': '2'},
                      {'type': 'subparagraph', 'id': 'A'},
                      {'type': 'paragraph', 'id': '4'},
                      {'type': 'subsection', 'id': 'b'},
                      {'type': 'section', 'id': '92-85'}],

                     [{'type': 'paragraph', 'id': '6'},
                      {'type': 'subsection', 'id': 'b'},
                      {'type': 'section', 'id': '92-85'}]
                    ],
            'impact': 'amended'
        }
    )
]


if __name__ == '__main__':
    unittest.main()
