import datetime
import re
from typing import Optional

import dateutil.parser
import pytz
from openstates.scrape import Event, Scraper

from utils.events import match_coordinates


class MTEventScraper(Scraper):
    """
    Montana events scraper.

    In mid-2025 Montana retired the old SLIQ/Harmony video portal
    (sg001-harmony.sliq.net) that this scraper used to rely on. Event data now
    lives across three separate JSON APIs, all of which are used here:

    1. The public WordPress site at www.legmt.gov exposes upcoming/past events
       via "The Events Calendar" plugin REST API. This gives us the canonical
       list of meetings with title, date/time, venue, and a `website` link that
       points at the Committee Explorer SPA
       (committees.legmt.gov/#/nonStandingCommittees/<id>).

    2. The Committee Explorer is backed by api-public.legmt.gov, whose
       committee-meetings search endpoints return each meeting's agenda items
       inline (title + description), keyed by committee id and meeting time.

    3. api-public.legmt.gov/docs exposes agenda and minutes PDF documents for a
       meeting; each document carries a direct download URL.
    """

    _tz = pytz.timezone("America/Denver")

    # WordPress "The Events Calendar" REST API
    _wp_events_url = "https://www.legmt.gov/wp-json/tribe/events/v1/events"

    # api-public.legmt.gov service roots
    _committees_api = "https://api-public.legmt.gov/committees/v1"
    _docs_api = "https://api-public.legmt.gov/docs/v1"
    _legislators_api = "https://api-public.legmt.gov/legislators/v1"

    _bill_re = re.compile(r"\b(?:SB|HB|SR|HR|SJ|HJ|LC)\s*\d+\b")

    # cache of legislatureId -> ordinal (e.g. 2 -> "69")
    _legislature_ordinals = {}
    # cache of (committee_type, committee_id) -> committee detail dict
    _committee_cache = {}
    # cache of (committee_type, committee_id) -> list of meeting dicts
    _meetings_cache = {}

    def scrape(self):
        self._load_legislatures()

        # Scrape a window around today: recent past meetings (which may now have
        # minutes/agenda documents attached) plus all upcoming meetings.
        today = datetime.date.today()
        start = today - datetime.timedelta(days=45)
        # The events calendar publishes meetings well into the future; grab a
        # generous window so we don't miss anything on the schedule.
        end = today + datetime.timedelta(days=365)

        seen = set()
        for event in self.scrape_events(start, end):
            # de-dupe on (name, start_date); the same meeting can occasionally
            # appear more than once in the source feed
            key = (event.name, event.start_date)
            if key in seen:
                continue
            seen.add(key)
            yield event

    def _load_legislatures(self):
        """Build a legislatureId -> ordinal lookup used by the docs API."""
        url = f"{self._legislators_api}/legislatures"
        for leg in self.get(url).json():
            # `ordinals` is a string like "69"
            self._legislature_ordinals[leg["id"]] = leg["ordinals"]

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
            # The API returns a 400 once you page past the last page.
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

        # ignore obvious test events
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

        # Only add a committee tag for real committee names, not bill hearings.
        if "HB" not in title and "SB" not in title:
            event.add_committee(title)

        # Attach agenda items and documents from the committee API, keyed by the
        # committee referenced in the WP event's `website` field.
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
        """Assemble a human-readable location from venue + room custom field."""
        parts = []

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
        """Match this event to a committee meeting and attach agenda + docs."""
        meetings = self._get_meetings(committee_type, committee_id)
        if not meetings:
            return

        meeting = self._match_meeting(meetings, when)
        if meeting is None:
            return

        # Agenda items come back inline on the meeting record.
        for item in meeting.get("agendaItems", []) or []:
            text = self._clean_text(item.get("title", ""))
            if not text:
                continue
            description = self._clean_text(item.get("description", ""))
            agenda = event.add_agenda_item(description or text)
            for bill in self._bill_re.findall(text):
                agenda.add_bill(self._normalize_bill_id(bill))

        # Agenda + minutes PDFs live in the docs service.
        committee = self._get_committee(committee_type, committee_id)
        if committee is not None:
            self._scrape_documents(event, committee, meeting)

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

        # Drop canceled meetings.
        meetings = [
            m for m in meetings if (m.get("status") or "").upper() != "CANCELED"
        ]

        self._meetings_cache[cache_key] = meetings
        return meetings

    def _match_meeting(self, meetings: list, when: datetime.datetime):
        """
        Find the meeting whose start matches the event. The committee API
        `meetingTime` is a naive local datetime string (America/Denver).
        We match on date, then prefer the closest start time.
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

    def _scrape_documents(self, event: Event, committee: dict, meeting: dict):
        """Fetch agenda + minutes PDFs for a meeting and attach them."""
        details = committee.get("committeeDetails") or {}
        code = details.get("committeeCode") or {}
        committee_code = code.get("code")
        type_code = (code.get("committeeType") or {}).get("code")
        if not committee_code or not type_code:
            return

        legislature_id = committee.get("legislatureId")
        ordinal = self._legislature_ordinals.get(legislature_id)
        if ordinal is None:
            return

        # standing committees carry a sessionId; interim committees do not
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
                name = doc.get("fileName") or f"{kind} document"
                event.add_document(
                    name,
                    download_url,
                    media_type="application/pdf",
                    on_duplicate="ignore",
                )

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
        # normalize HTML entities the WP API returns (e.g. &#8217;)
        import html

        text = html.unescape(text)
        text = re.sub(r"\s+\u2013\s+", " - ", text)
        return re.sub(r"\s+", " ", text).strip()
