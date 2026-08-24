import os
import unittest

import lxml.html

from ..bills import (
    version_folder_code,
    version_html_url_template,
    version_pdf_url_template,
)

here = os.path.dirname(__file__)


def load_fixture(name):
    path = os.path.join(here, "fixtures", name)
    with open(path) as f:
        return lxml.html.fromstring(f.read())


class TestVersionFolderCode(unittest.TestCase):
    def test_single_letter_abbrev(self):
        self.assertEqual(version_folder_code("e"), "E")
        self.assertEqual(version_folder_code("i"), "I")
        self.assertEqual(version_folder_code("r"), "R")

    def test_multi_letter_abbrev_uses_first_letter_only(self):
        # "Enrolled with Governor's Action" -> value "eg", folder is
        # still LGE, not LGEG
        self.assertEqual(version_folder_code("eg"), "E")
        # "Reprinted Marked Up" -> value "rm", folder is still LGR, not LGRM
        self.assertEqual(version_folder_code("rm"), "R")


class TestBillVersionUrls(unittest.TestCase):
    def _version_urls(self, fixture_name, session_id="91", bill_id="HF2558"):
        page = load_fixture(fixture_name)
        urls = {}
        for option in page.xpath('//select[@id="billVersions"]/option'):
            version_name = option.text
            version_abbrev = option.xpath("string(@value)")
            folder_code = version_folder_code(version_abbrev)
            urls[version_name] = {
                "html": version_html_url_template.format(
                    folder_code, session_id, bill_id
                ),
                "pdf": version_pdf_url_template.format(
                    folder_code, session_id, bill_id
                ),
            }
        return urls

    def test_hf2558_enrolled_with_governors_action_uses_lge(self):
        urls = self._version_urls("billbook_hf2558.html")
        gov_urls = urls["Enrolled with Governor's Action"]
        self.assertIn("/publications/LGE/91/", gov_urls["html"])
        self.assertIn("/publications/LGE/91/", gov_urls["pdf"])
        self.assertNotIn("LGEG", gov_urls["html"])
        self.assertNotIn("LGEG", gov_urls["pdf"])

    def test_sf259_reprinted_marked_up_uses_lgr(self):
        urls = self._version_urls("billbook_sf259.html", bill_id="SF259")
        rm_urls = urls["Reprinted Marked Up"]
        self.assertIn("/publications/LGR/91/", rm_urls["html"])
        self.assertIn("/publications/LGR/91/", rm_urls["pdf"])
        self.assertNotIn("LGRM", rm_urls["html"])
        self.assertNotIn("LGRM", rm_urls["pdf"])


if __name__ == "__main__":
    unittest.main()
