import unittest
import pprint

import parse


class TestRelatedCitation(unittest.TestCase):

    def test_parse_all(self):
        for string, data in samples:
            print 'test-data'
            pprint.pprint(data)
            _data = parse.parse(string)
            print 'parsed-data'
            pprint.pprint(_data)
            self.assertEqual(data, _data)


samples = [

    ('Section 32 of the labor law is amended to read as follows:',
        {
            'type': 'statute',
            'id': 'labor law',
            'nodes': [
                [{'type': 'section', 'id': '32'}]
                ],
            'verb': 'amended'
        }
    ),

    (('Section 191-b of the labor law, as added by chapter 451 of '
      'the laws of 1987, is amended to read as follows:'),
        {
            'type': 'statute',
            'id': 'labor law',
            'nodes': [
                [{'type': 'section', 'id': '191-b'}]
                ],
            'verb': 'amended'
        }
    ),

    (('Subdivision 1 of section 100 of the labor law, as amended '
      'by chapter 757 of the laws of 1975, is amended to read as follows:'),
        {
            'type': 'statute',
            'id': 'labor law',
            'nodes': [
                [{'type': 'subdivision', 'id': '100'}]
                ],
            'verb': 'amended'
        }
    ),

    (('Subdivision 1 of section 21 of the labor law, added by section '
      '146 of part B of chapter 436 of the laws of 1997 and renumbered by '
      'chapter 214 of the laws of 1998, is amended to read as follows:'),
        {
            'type': 'statute',
            'id': 'labor law',
            'nodes': [
                [{'type': 'subdivision', 'id': '1'},
                 {'type': 'section', 'id': '21'}]
                ],
            'verb': 'amended'
        }
    ),

    (('Section 57-0131 of the environmental conservation law, as amended '
      'by chapter 286 of the laws of 1998, is amended to read as follows:'),
        {
            'type': 'statute',
            'id': 'environmental conservation law',
            'nodes': [[{'type': 'section', 'id': '57-0131'}]],
            'verb': 'amended'
        }
    ),

    (('Subdivision 4 of section 30 of the labor law, as amended by '
      'chapter 756 of the laws of 1975 and renumbered by chapter 162 '
      'of the laws of 1993, is amended to read as follows:'),
        {
            'id': 'labor law',
            'type': 'statute',
            'nodes': [
                [{'type': 'subdivision', 'id': '4'},
                 {'type': 'section', 'id': '30'}]
                ],
            'verb': 'amended'
        }
    ),

    ('Section 30 of the labor law is renumbered section 60.',
        {
            'id': 'labor law',
            'type': 'statute',
            'nodes': [
                [{'type': 'section', 'id': '30'}]
                ],
            'verb': 'renumbered',
            'info': [
                [{'type': 'setion', 'id': '60'}]
                ]
        }
    ),

    (('Subdivision 1 of section 20 of chapter 784 of the laws of 1951,'
      'constituting the New York state defense emergency act, is '
      'amended to read as follows:'),
        {
            'chapter': '784',
            'year': '1951',
            'type': 'session_law',
            'nodes': [
                [{'type': 'section', 'id': '20'}]
                ],
            'verb': 'amended',
        }
    ),

    (('Subdivision 1 of section 20 of chapter 784 of the laws of '
      '1951, constituting the New York state defense emergency act, '
      'as amended by chapter 3 of the laws of 1961, is amended to '
      'read as follows:'),
        {
            'chapter': '784',
            'year': '1951',
            'type': 'session_law',
            'nodes': [
                [{'type': 'subdivision', 'id': '1'},
                 {'type': 'section', 'id': '20'}],
                ],
            'name': 'New York state defense emergency act',
            'verb': 'amended',
        }
    ),

    (('Section 4 of chapter 694 of the laws of 1962, relating to the '
      'transfer of judges to the civil court of the city of New York, '
      'is amended to read as follows:'),
        {
            'chapter': '694',
            'year': '1962',
            'type': 'session_law',
            'nodes': [
                [{'type': 'section', 'id': '4'}],
                ],
            'verb': 'amended',
        }
    ),

    (('Section 4502 of the public health law, as added by a chapter '
      'of the laws of 1989, amending the public health law relating '
      'to health foods, as proposed in legislative bill number S. '
      '3601, is amended to read as follows:'),
        {
            'id': 'public health law',
            'type': 'statute',
            'nodes': [
                [{'type': 'section', 'id': '4502'}]
                ],
            'verb': 'amended',
        }
    ),

    (('Section 4508 of the public health law, as added by a chapter '
      'of the laws of 1989, amending the public health law relating '
      'to health foods, as proposed in legislative bill number S. 3601, '
      'is amended to read as follows:'),
        {
            'id': 'public health law',
            'type': 'statute',
            'nodes': [
                [{'type': 'section', 'id': '4508'}]
                ],
            'verb': 'amended',
        }
    ),

    (('Section 3 of a chapter 234 of the laws of 1989, amending the public '
      'health law relating to the sale of health foods, as proposed in '
      'legislative bill number A. 5730, is amended to read as follows:'),
        {
            'chapter': '234',
            'year': '1989',
            'type': 'session_law',
            'nodes': [
                [{'type': 'section', 'id': '3'}]
                ],
            'verb': 'amended',
        }
    ),

    (('Section 4 of a chapter 234 of the laws of 1989, amended the public '
      'health law relating to the sale of health foods, as proposed in '
      'legislative bill number A. 5730, is amended to read as follows:'),
        {
            'chapter': '234',
            'year': '1989',
            'type': 'session_law',
            'nodes': [
                [{'type': 'section', 'id': '4'}]
                ],
            'verb': 'amended',
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
            'types': 'statute',
            'nodes': [
                [{'type': 'section', 'id': '4502'}]
                ],
            'verb': 'amended',
        }
    ),

    (('Sections 16-a and 18-a of the general construction law, as added '
      'by chapter 917 of the laws of 1920, are mended to read as follows:'),
        {
            'id': 'general construction law',
            'types': 'statute',
            'nodes': [
                [{'type': 'section', 'id': '16-a'}],
                [{'type': 'section', 'id': '18-a'}]
                ],
            'verb': 'amended',
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
            'types': 'statute',
            'nodes': [
                [{'type': 'section', 'id': '631'}],
                ],
            'verb': 'amended',
        }
    ),

    (('Section 27-1018 of the administrative code of the city of New '
      'York, subdivisions c, d and e as added by local law number 61 of '
      'the city of New York for the year 1987, is amended to read as '
      'follows:'),
        {
            'id': 'administrative code of the city of New York',
            'type': 'statute',
            'nodes': [
                [{'type': 'subdivision', 'id': 'c'},
                 {'type': 'section', 'id': '27-1018'}],
                [{'type': 'subdivision', 'id': 'd'},
                 {'type': 'section', 'id': '27-1018'}],
                [{'type': 'subdivision', 'id': 'e'},
                 {'type': 'section', 'id': '27-1018'}]
                ],
            'verb': 'amended'
        }
    ),

    (('Paragraph 2, subparagraph (A) of paragraph 4, and paragraph 6 of '
      'subsection (b) of section 92-85 of the codes and ordinances of the '
      ' city of Yonkers, paragraph 2 and subparagraph (A) of paragraph 4 '
      'as added by local law number 8 and paragraph 6 as amended by local '
      'law number 9 of the city of Yonkers for the year 1984, are amended '
      'to read as follows:'),
        {
            'type': 'statute',
            'id': 'codes and ordinances of the city of Yonkers',
            'nodes': [[{'type': 'paragraph', 'id': '2'},
                      {'type': 'subparagraph', 'id': 'A'},
                      {'type': 'paragraph', 'id': '4'},
                      {'type': 'subsection', 'id': 'b'},
                      {'type': 'section', 'id': '92-85'}],

                     [{'type': 'paragraph', 'id': '6'},
                      {'type': 'subsection', 'id': 'b'},
                      {'type': 'section', 'id': '92-85'}]
                    ],
            'verb': 'amended'
        }
    )
]


if __name__ == '__main__':
    unittest.main()
