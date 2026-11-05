import lxml.html

from openstates.scrape import Bill

from ..bills import NCBillScraper


def make_bill():
    bill = Bill(
        identifier="S 257",
        legislative_session="2025",
        title="Test bill",
        chamber="upper",
        classification="bill",
    )
    bill.add_source("https://www.ncleg.gov/BillLookup/2025/S257")
    return bill


def test_add_version_documents():
    page = lxml.html.fromstring(
        """
        <div class="card-body">
          <div class="row">
            <div class="col-6">
              <a href="/Sessions/2025/Bills/Senate/PDF/S257v2.pdf">Edition 2</a>
              <a class="sr-only" href="/Sessions/2025/Bills/Senate/RTF/S257v2.rtf">
                Download Edition 2 in RTF
              </a>
            </div>
            <div class="col-6">
              <a href="/Sessions/2025/FiscalNotes/Senate/PDF/SFN257v2.pdf">
                Fiscal Note
              </a>
              <a href="/Sessions/2025/FiscalNotes/Senate/PDF/SIN257v2.pdf">
                Incarceration
              </a>
            </div>
          </div>
        </div>
        """
    )
    page.make_links_absolute("https://www.ncleg.gov/BillLookup/2025/S257")
    bill = make_bill()

    NCBillScraper.add_version_documents(None, bill, page)

    assert [document["note"] for document in bill.documents] == [
        "Edition 2 Fiscal Note",
        "Edition 2 Incarceration",
    ]
    assert all(
        document["links"][0]["media_type"] == "application/pdf"
        for document in bill.documents
    )
    bill.validate()


def test_add_action_documents_and_adopted_amendment():
    row = lxml.html.fromstring(
        """
        <div class="row avoid-break-inside">
          <div>Date:</div><div>5/21/2025</div>
          <div>Chamber:</div><div>House</div>
          <div>Action:</div><div>Amend Adopted A23</div>
          <div>Documents:</div>
          <div>
            <a href="https://example.com/amendment.pdf" title="Amendment">
              <b>A23:</b> AMQ-16-V-18
            </a>
            <a href="https://example.com/fiscal.pdf" title="Fiscal Note">
              <b>FD:</b> Fiscal Note
            </a>
            <a href="https://example.com/report.pdf" title="Conference Report">
              <b>CR:</b> Conference Report
            </a>
          </div>
          <div>Votes:</div><div>None</div>
        </div>
        """
    )
    bill = make_bill()

    NCBillScraper.add_action_documents(None, bill, row, "Amend Adopted A23")

    assert [document["note"] for document in bill.documents] == [
        "Amend Adopted A23 AMQ-16-V-18",
        "Amend Adopted A23 Fiscal Note",
        "Amend Adopted A23 Conference Report",
    ]
    assert all(
        document["links"][0]["media_type"] == "application/pdf"
        for document in bill.documents
    )
    assert [document["classification"] for document in bill.documents] == [
        "",
        "fiscal-note",
        "committee-report",
    ]
    assert bill.versions == [
        {
            "note": "Adopted Amendment A23: AMQ-16-V-18",
            "date": "",
            "classification": "amendment",
            "links": [
                {
                    "url": "https://example.com/amendment.pdf",
                    "media_type": "application/pdf",
                }
            ],
        }
    ]
    bill.validate()


def test_non_adopted_amendment_is_only_a_document():
    row = lxml.html.fromstring(
        """
        <div class="row">
          <div>Documents:</div>
          <div>
            <a href="https://example.com/amendment.pdf" title="Amendment">
              <b>A45:</b> AMT-55-V-3
            </a>
          </div>
        </div>
        """
    )
    bill = make_bill()

    NCBillScraper.add_action_documents(None, bill, row, "Amend Tabled A45")

    assert bill.documents[0]["note"] == "Amend Tabled A45 AMT-55-V-3"
    assert bill.versions == []
    bill.validate()
