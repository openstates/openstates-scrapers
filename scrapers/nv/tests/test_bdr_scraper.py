import json
from unittest import mock

from ..bills import NVBillScraper


BDR_ROWS = b"""
<div class="bdr-container search-region">
  <div class="row mx-0">
    <div class="col-md-1">52-615<br /></div>
    <div class="col">
      <span class="font-weight-bold"> Assemblymember Nadeem</span><br />
      Imposes requirements relating to prescription drugs.<div></div>
    </div>
    <div class="col-sm-1"></div>
    <div class="col-sm-2">10/21/2026<br /><small></small></div>
  </div>
  <div class="row mx-0">
    <div class="col-md-1">S-605<br />
      <a href="/Bill/13015/Overview"><span>SB1</span></a>
    </div>
    <div class="col">
      <span class="font-weight-bold"> Legislative Counsel</span><br />
      Makes an appropriation.<div></div>
    </div>
    <div class="col-sm-1"></div>
    <div class="col-sm-2">9/30/2026<br /><small></small></div>
  </div>
  <div class="row mx-0">
    <div class="col-md-1">40-620<br /></div>
    <div class="col">
      <span class="font-weight-bold"> Department of Testing</span><br />
      Revises provisions relating to tests.<div></div>
    </div>
    <div class="col-sm-1"></div>
    <div class="col-sm-2">10/23/2026<br /><small></small></div>
  </div>
  <div class="row mx-0">
    <div class="col-md-1">57-621<br /></div>
    <div class="col">
      <span class="font-weight-bold"> Senator Do&#241;ate</span><br />
      Revises provisions relating to insurance.<div></div>
    </div>
    <div class="col-sm-1"></div>
    <div class="col-sm-2">10/24/2026<br /><small></small></div>
  </div>
</div>
"""


def test_scrape_bdrs_skips_linked_bills_and_builds_requested_fields():
    scraper = NVBillScraper.__new__(NVBillScraper)
    scraper.get = mock.Mock(return_value=mock.Mock(content=BDR_ROWS))

    bills = list(scraper.scrape_bdrs("84", "84th2027"))

    assert [bill.identifier for bill in bills] == ["52-615", "40-620", "57-621"]

    assembly_bdr = bills[0]
    assert assembly_bdr.title == "Imposes requirements relating to prescription drugs."
    assert assembly_bdr.from_organization == '~{"classification": "legislature"}'
    assert assembly_bdr.sponsorships[0]["name"] == "Nadeem"
    assert assembly_bdr.sponsorships[0]["entity_type"] == "person"
    assert json.loads(assembly_bdr.sponsorships[0]["person_id"][1:]) == {
        "chamber": "lower",
        "name": "Nadeem",
    }
    assert assembly_bdr.actions[0]["description"] == "Filed"
    assert assembly_bdr.actions[0]["classification"] == ["filing"]
    assert assembly_bdr.actions[0]["date"].strftime("%Y-%m-%d") == "2026-10-21"

    organization_bdr = bills[1]
    assert organization_bdr.sponsorships[0]["name"] == "Department of Testing"
    assert organization_bdr.sponsorships[0]["entity_type"] == "organization"

    senate_bdr = bills[2]
    assert senate_bdr.sponsorships[0]["name"] == "Doñate"
    assert senate_bdr.sponsorships[0]["entity_type"] == "person"
    assert json.loads(senate_bdr.sponsorships[0]["person_id"][1:]) == {
        "chamber": "upper",
        "name": "Doñate",
    }

    for bill in bills:
        bill.validate()
