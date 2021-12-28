import lxml.html

from openstates.scrape import Scraper, Organization
from .apiclient import ApiClient
from .utils import get_with_increasing_timeout
from scrapelib import HTTPError


class INCommitteeScraper(Scraper):
    jurisdiction = "in"

    _parent_committees = {}

    def process_special_members(self, comm, comm_json, role_name):
        role_dict = {
            "chair": "Chair",
            "viceChair": "Vice Chair",
            "rankingMinMember": "Ranking Minority Member",
        }
        try:
            mem = comm_json[role_name]
        except KeyError:
            return
        if mem:
            person = mem["firstName"] + " " + mem["lastName"]
            comm.add_member(person, role=role_dict[role_name])
            return person
        return None

    def get_subcommittee_info(self, session):
        # api gives NO way of finding out who owns
        # a subcommittee. It can be found based in indenting(!)
        # here: http://iga.in.gov/legislative/2015/committees/standing
        # so we're going to hit that and make a dictionary. yuck

        # but this is less important than some other stuff
        # so we're going to be OK if we timeout.
        link = "http://iga.in.gov/legislative/{}/committees/standing".format(session)
        html = get_with_increasing_timeout(self, link, fail=False)
        sc_dict = {}
        if html:
            doc = lxml.html.fromstring(html.text)
            committees = doc.xpath("//li[@class='committee-item']")
            for c in committees:
                comm_name = c.xpath("./a")[0]
                comm_name = comm_name.text_content().strip()
                subcomms = c.xpath(".//li[@class='subcommittee-item']")
                for s in subcomms:
                    subcom_name = s.text_content().strip()
                    sc_dict[subcom_name] = comm_name

        return sc_dict

    def scrape(self, session):
        subcomms = self.get_subcommittee_info(session)

        api_base_url = "https://api.iga.in.gov"
        html_base_url = "http://iga.in.gov/legislative/{}/committees/".format(session)
        client = ApiClient(self)
        r = client.get("committees", session=session)
        all_pages = client.unpaginate(r)
        for comm_info in all_pages:
            # this is kind of roundabout, but needed in order
            # to take advantage of all of our machinery to make
            # sure we're not overloading their api
            comm_link = comm_info["link"]
            comm_name = comm_link.split("/")[-1]
            if "withdrawn" in comm_name or "conference" in comm_name:
                continue
            try:
                comm_json = client.get("committee", committee_link=comm_link[1:])
            except HTTPError:
                self.logger.warning("Page does not exist")
                continue
            try:
                chamber = comm_json["chamber"]["name"]
            except KeyError:
                chamber = "joint"
            else:
                if chamber == "Senate":
                    chamber = "upper"
                elif chamber == "House":
                    chamber = "lower"
                else:
                    raise AssertionError("Unknown committee chamber {}".format(chamber))

            name = comm_json["name"]
            try:
                owning_comm = subcomms[name]
            except KeyError:
                name = name.replace("Statutory Committee on", "").strip()
                comm = Organization(
                    name=name, chamber=chamber, classification="committee"
                )
                if name in subcomms.values():
                    # Avoid identification issues, if committee names are re-used
                    # between upper and lower chambers
                    assert self._parent_committees.get(name) is None
                    self._parent_committees[name] = comm
            else:
                name = (
                    name.replace("Statutory Committee on", "")
                    .replace("Subcommittee", "")
                    .strip()
                )
                comm = Organization(
                    name=name,
                    parent_id=self._parent_committees[owning_comm],
                    classification="committee",
                )

            chair = self.process_special_members(comm, comm_json, "chair")
            vicechair = self.process_special_members(comm, comm_json, "viceChair")
            ranking = self.process_special_members(comm, comm_json, "rankingMinMember")

            # leadership is also listed in membership
            # so we have to make sure we haven't seen them yet
            comm_members = [m for m in [chair, vicechair, ranking] if m]

            for mem in comm_json["members"]:
                mem_name = mem["firstName"] + " " + mem["lastName"]
                if mem_name not in comm_members:
                    comm_members.append(mem_name)
                    comm.add_member(mem_name)

            api_source = api_base_url + comm_link

            if comm_name[:10] == "committee_":
                html_source = html_base_url + comm_name[10:]

            comm.add_source(html_source)
            comm.add_source(api_source)
            yield comm
