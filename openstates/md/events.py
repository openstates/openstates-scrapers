import datetime as dt

from openstates.utils import LXMLMixin
from billy.scrape.events import Event, EventScraper

import re
import pytz
import lxml.html


def last_space(string):
    # this is a big hack.
    for x in range(0, len(string)):
        if string[x] != " ":
            return x
    return None


class MDEventScraper(EventScraper, LXMLMixin):
    jurisdiction = 'md'
    _tz = pytz.timezone('US/Eastern')

    def scrape(self, chamber, session):
        self.logger.warning("MD's events schedule is a blob of hand-indented text and has changed from last year. Skipping for now.")
        return



        if chamber != 'other':
            return None  # We're going to do it all on one shot.

        if session[-2:] == "s1":
            return None  # Special sessions 404

        url = "http://mlis.state.md.us/%s/hearsch/alladd.htm" % ( session )
        page = self.lxmlize(url)
        events = page.xpath("//pre")
        for event in events:
            ctty_name = [
                x.strip() for x in
                event.getparent().getprevious().text_content().split("-", 1)
            ]
            ctty_name = ctty_name[0]
            event_text = event.text_content()
            if "This meeting has been cancelled." in event_text:
                continue
            # OK. In order to process this text-only notice, we have to resort
            # to some major hackage. Just roll with it.
            lines = event_text.split("\n")
            # In order to get the key stuff, we need to figure out where the
            # address "block" starts.
            address_block = last_space(lines[4])
            assert address_block is not None
            # OK. Given the offset, we can "split" the time off the date block.
            time_room = lines[3]
            time = time_room[:address_block].strip()

            if "TBD" in time:
                continue  # Nothing's set yet.
            time = "%s %s" % (
                lines[1],
                time
            )
            time = re.sub("\s+", " ", time).strip()
            trans = {
                "P.M." : "PM",
                "A.M." : "AM"
            }
            for transition in trans:
                time = time.replace(transition, trans[transition])

            when = dt.datetime.strptime(time, "%A %B %d, %Y %I:%M %p")

            room = time_room[address_block:].strip()
            place_block = lines[4:]
            where = room + "\n"
            done = False
            offset = 4
            for place in place_block:
                if place.strip() == "":
                    done = True
                if done:
                    continue
                offset += 1
                where += place.strip() + "\n"
            where = where.strip()
            # Now that the date's processed, we can move on.
            moreinfo = lines[offset + 1:]
            info = {}
            key = "unattached_header"
            for inf in moreinfo:
                if ":" in inf:
                    key, value = inf.split(":", 1)
                    key = key.strip()
                    info[key] = value.strip()
                else:
                    info[key] += " " + inf.strip()
            # Alright. We should have enough now.
            subject = info['Subject']

            event = Event(session, when, 'committee:meeting',
                          subject, location=where)
            event.add_source(url)

            flags = {
                "joint": "joint",
                "house": "lower",
                "senate": "upper"
            }
            chamber = "other"
            for flag in flags:
                if flag in ctty_name.lower():
                    chamber = flags[flag]

            # Let's try and hack out some bill names.
            trans = {
                "SENATE": "S",
                "HOUSE": "H",
                "JOINT": "J",
                "BILL": "B",
                "RESOLUTION": "R",
            }
            _t_subject = subject.upper()
            for t in trans:
                regex = "%s(\s+)?" % t
                _t_subject = re.sub(regex, trans[t], _t_subject)
            print _t_subject
            bills = re.findall("(S|H)(J)?(B|R|M)\s*(\d{4})", _t_subject)
            for bill in bills:
                name = bill[:3]
                bid = bill[3]
                bill_id = "%s %s" % ( ''.join(name), bid )
                event.add_related_bill(bill_id,
                                       description=subject,
                                       type='consideration')


            event.add_participant("host", ctty_name, 'committee',
                                  chamber=chamber)

            self.save_event(event)
