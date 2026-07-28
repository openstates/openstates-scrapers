import datetime
import html
import re
from typing import Optional

import dateutil.parser
import pytz
from openstates.scrape import Event, Scraper

from utils.events import match_coordinates


class MTEventScraper(Scraper):
    """Montana events.

    MT shut down the old SLIQ/Harmony portal (sg001-harmony.sliq.net) in
    mid-2025, so we now piece events together from three sources:

    - the legmt.gov WordPress site ("The Events Calendar" plugin) for the event
      list itself -- title, time, venue, and a link to the committee page
    - api-public.legmt.gov committee endpoints for the matching meeting record,
      which includes agenda items inline
    - api-public.legmt.gov/docs for the agenda / minutes PDFs
    """

    _tz = pytz.timezone("America/Denver")

    _wp_events_url = "https://www.legmt.gov/wp-json/tribe/events/v1/events"
    _committees_api = "https://api-public.legmt.gov/committees/v1"
    _docs_api = "https://api-public.legmt.gov/docs/v1"

    _bill_re = re.compile(r"\b(?:SB|HB|SR|HR|SJ|HJ|LC)\s*\d+\b")

    # The committee API's inline agenda items double as a staff scratchpad, so a
    # meeting a year out can already carry a full "agenda" that nobody's actually
    # published yet. When there's no published agenda PDF to back it up, only
    # trust those items if the meeting is within this many days (or already past).
    _agenda_trust_window_days = 14

    _committee_cache = {}  # (committee_type, committee_id) -> committee dict
    _meetings_cache = {}  # (committee_type, committee_id) -> [meeting dict]

    def scrape(self):
        # The docs API wants a legislature "ordinal" (e.g. 69). Rather than hit
        # another endpoint for it, pull it from the session metadata we already
        # keep in __init__.py. The API's legislatureId lines up with the
        # session's newAPIIdentifier.
        self._legislature_ordinals = {
            session["extras"]["newAPIIdentifier"]: session["extras"][
                "legislatureOrdinal"
            ]
            for session in self.jurisdiction.legislative_sessions
            if session.get("extras", {}).get("newAPIIdentifier") is not None
        }

        # Look back far enough to catch minutes/agendas that show up after a
        # meeting, and forward far enough to cover the published schedule.
        today = datetime.date.today()
        start = today - datetime.timedelta(days=45)
        end = today + datetime.timedelta(days=365)

        seen = set()
        for event in self.scrape_events(start, end):
            # the feed occasionally lists the same meeting twice
            key = (event.name, event.start_date)
            if key in seen:
                continue
            seen.add(key)
            yield event

    def scrape_events(self, start: datetime.date, end: datetime.date):
        """Page through the WordPress events REST API for the given window."""
        page = 1
        while True:
            params = {
                "start_date": start.strftime("%Y-%m-%d"),
                "end_date": end.strftime("%Y-%m-%d"),
                "per_page": 50,
                "page": page,
            }
            resp = self.get(self._wp_events_url, params=params)
            # paging past the last page returns a 400
            if resp.status_code != 200:
                break
            data = resp.json()
            events = data.get("events", [])
            if not events:
                break
            for row in events:
                event = self.scrape_event(row)
                if event is not None:
                    yield event
            if page >= data.get("total_pages", page):
                break
            page += 1

    def scrape_event(self, row: dict) -> Optional[Event]:
        title = self._clean_text(row["title"])

        # skip placeholder/test events
        if title.lower() in ("test", "other"):
            return None

        when = dateutil.parser.parse(row["start_date"])
        when = self._tz.localize(when)

        end = None
        if row.get("end_date"):
            end = self._tz.localize(dateutil.parser.parse(row["end_date"]))

        location = self._build_location(row)

        event = Event(
            name=title,
            location_name=location,
            start_date=when,
            end_date=end,
            classification="committee-meeting",
            upstream_id=str(row["id"]),
        )
        event.add_source(row["url"])

        # bill hearings get titled after the bill, not a committee
        if "HB" not in title and "SB" not in title:
            event.add_committee(title)

        # the event links back to a committee; use that to pull agenda + docs
        committee_ref = self._parse_committee_ref(row.get("website"))
        if committee_ref is not None:
            committee_type, committee_id = committee_ref
            self.scrape_committee_meeting(event, committee_type, committee_id, when)

        match_coordinates(
            event,
            {
                "1301 E 6th Ave, Helena": ("46.5857", "-112.0184"),
                "State Capitol": ("46.5857", "-112.0184"),
            },
        )

        return event

    def _build_location(self, row: dict) -> str:
        """Build a location string from the venue plus the room custom field."""
        parts = []

        # room lives in a custom field, not the venue block
        room = None
        custom = row.get("custom_fields") or {}
        for field in custom.values():
            if field.get("label", "").lower() == "room" and field.get("value"):
                room = field["value"]
                break
        if room:
            parts.append(room)

        venue = row.get("venue") or {}
        if isinstance(venue, dict) and venue.get("venue"):
            addr_bits = [
                venue.get("venue"),
                venue.get("address"),
                venue.get("city"),
                venue.get("state"),
                venue.get("zip"),
            ]
            parts.append(", ".join(b for b in addr_bits if b))

        location = ", ".join(parts).strip()
        return location or "See source for location"

    @staticmethod
    def _parse_committee_ref(website: Optional[str]):
        """
        Parse a Committee Explorer link like
        https://committees.legmt.gov/#/nonStandingCommittees/2
        into ("nonStandingCommittees", 2).
        """
        if not website:
            return None
        match = re.search(
            r"#/(nonStandingCommittees|standingCommittees)/(\d+)", website
        )
        if not match:
            return None
        return match.group(1), int(match.group(2))

    def scrape_committee_meeting(
        self,
        event: Event,
        committee_type: str,
        committee_id: int,
        when: datetime.datetime,
    ):
        """Attach agenda items and documents for the matching committee meeting."""
        meetings = self._get_meetings(committee_type, committee_id)
        if not meetings:
            return

        meeting = self._match_meeting(meetings, when)
        if meeting is None:
            return

        # Grab the PDFs first -- whether a published agenda exists tells us
        # whether the inline agenda items below can be trusted.
        has_published_agenda = False
        committee = self._get_committee(committee_type, committee_id)
        if committee is not None:
            has_published_agenda = self._scrape_documents(event, committee, meeting)

        # The inline agenda items are only reliable once someone could actually
        # go look them up: either there's a published agenda PDF, or the meeting
        # is close enough that the agenda is effectively set. Otherwise we still
        # keep the event and its documents, we just leave off the draft agenda.
        if has_published_agenda or self._meeting_within_trust_window(when):
            for item in meeting.get("agendaItems", []) or []:
                text = self._clean_text(item.get("title", ""))
                if not text:
                    continue
                description = self._clean_text(item.get("description", ""))
                agenda = event.add_agenda_item(description or text)
                for bill in self._bill_re.findall(text):
                    agenda.add_bill(self._normalize_bill_id(bill))

    def _meeting_within_trust_window(self, when: datetime.datetime) -> bool:
        """Whether the meeting is past or close enough to trust its agenda."""
        cutoff = datetime.datetime.now(self._tz) + datetime.timedelta(
            days=self._agenda_trust_window_days
        )
        return when <= cutoff

    def _get_meetings(self, committee_type: str, committee_id: int):
        cache_key = (committee_type, committee_id)
        if cache_key in self._meetings_cache:
            return self._meetings_cache[cache_key]

        if committee_type == "nonStandingCommittees":
            url = f"{self._committees_api}/nonStandingCommitteeMeetings/search"
            body = {"nonStandingCommitteeIds": [committee_id]}
        else:
            url = f"{self._committees_api}/standingCommitteeMeetings/search"
            body = {"standingCommitteeIds": [committee_id]}

        meetings = []
        offset = 0
        while True:
            resp = self.post(
                url,
                json=body,
                params={"limit": 150, "offset": offset},
            )
            if resp.status_code != 200:
                break
            data = resp.json()
            if isinstance(data, dict):
                content = data.get("content", [])
                total_pages = data.get("totalPages", 1)
            else:
                content = data
                total_pages = 1
            meetings.extend(content)
            offset += 1
            if offset >= total_pages:
                break

        meetings = [
            m for m in meetings if (m.get("status") or "").upper() != "CANCELED"
        ]

        self._meetings_cache[cache_key] = meetings
        return meetings

    def _match_meeting(self, meetings: list, when: datetime.datetime):
        """Pick the meeting matching this event's start time.

        meetingTime comes back as a naive local (America/Denver) string, so we
        match on the date and then take whichever start time is closest.
        """
        target = when.replace(tzinfo=None)
        candidates = []
        for m in meetings:
            mt = m.get("meetingTime")
            if not mt:
                continue
            try:
                m_dt = dateutil.parser.parse(mt)
            except (ValueError, TypeError):
                continue
            if m_dt.date() == target.date():
                candidates.append((abs((m_dt - target).total_seconds()), m))

        if not candidates:
            return None
        candidates.sort(key=lambda c: c[0])
        return candidates[0][1]

    def _get_committee(self, committee_type: str, committee_id: int):
        cache_key = (committee_type, committee_id)
        if cache_key in self._committee_cache:
            return self._committee_cache[cache_key]

        if committee_type == "nonStandingCommittees":
            url = f"{self._committees_api}/nonStandingCommittees/{committee_id}"
        else:
            url = f"{self._committees_api}/standingCommittees/{committee_id}"

        resp = self.get(url)
        committee = resp.json() if resp.status_code == 200 else None
        self._committee_cache[cache_key] = committee
        return committee

    def _scrape_documents(self, event: Event, committee: dict, meeting: dict) -> bool:
        """Attach agenda + minutes PDFs, returning whether an agenda was found.

        The agenda result is what the caller uses to decide whether the inline
        agenda items are trustworthy.
        """
        details = committee.get("committeeDetails") or {}
        code = details.get("committeeCode") or {}
        committee_code = code.get("code")
        type_code = (code.get("committeeType") or {}).get("code")
        if not committee_code or not type_code:
            return False

        legislature_id = committee.get("legislatureId")
        ordinal = self._legislature_ordinals.get(legislature_id)
        if ordinal is None:
            return False

        # standing committees carry a sessionId, interim committees don't
        committee_type = "STANDING" if "sessionId" in meeting else "NON-STANDING"

        chamber = committee.get("chamber", "") or ""
        meeting_time = meeting.get("meetingTime", "")

        params = {
            "legislatureOrdinal": ordinal,
            "committeeType": committee_type,
            "committeeTypeCode": type_code,
            "committeeCode": committee_code,
            "chamber": chamber,
            "meetingDateTime": meeting_time,
        }

        found_agenda = False
        for kind, endpoint in (
            ("Agenda", "getMeetingAgendas"),
            ("Minutes", "getMeetingMinutes"),
        ):
            url = f"{self._docs_api}/documents/{endpoint}"
            resp = self.get(url, params=params)
            if resp.status_code != 200:
                continue
            for doc in resp.json():
                download_url = self._document_url(doc)
                if not download_url:
                    continue
                if kind == "Agenda":
                    found_agenda = True
                name = doc.get("fileName") or f"{kind} document"
                event.add_document(
                    name,
                    download_url,
                    media_type="application/pdf",
                    on_duplicate="ignore",
                )

        return found_agenda

    @staticmethod
    def _normalize_bill_id(raw: str) -> str:
        """Turn "HB70" / "SB  191" into the canonical "HB 70" / "SB 191"."""
        match = re.match(r"([A-Z]+)\s*(\d+)", raw.strip())
        if not match:
            return re.sub(r"\s+", " ", raw).strip()
        return f"{match.group(1)} {match.group(2)}"

    @staticmethod
    def _document_url(doc: dict) -> Optional[str]:
        """Extract the direct download URL from a docs-API document object."""
        for attr in doc.get("attributes", []) or []:
            if attr.get("name") == "DocumentLink" and attr.get("stringValue"):
                return attr["stringValue"]
        return None

    @staticmethod
    def _clean_text(text: str) -> str:
        if not text:
            return ""
        # the WP API hands back HTML entities like &#8217;
        text = html.unescape(text)
        text = re.sub(r"\s+\u2013\s+", " - ", text)
        return re.sub(r"\s+", " ", text).strip()
