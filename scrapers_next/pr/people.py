from spatula import URL, CSS, HtmlListPage
from openstates.models import ScrapePerson
import re


class Senate(HtmlListPage):
    source = URL("https://senado.pr.gov/Pages/Senadores.aspx")
    selector = CSS("ul.senadores-list li")

    def process_item(self, item):
        name = CSS("span.name").match_one(item).text_content().strip()
        # Convert to title case as some names are in all-caps
        name = re.sub(r"^Hon\.", "", name, flags=re.IGNORECASE).strip().title()

        party = CSS("span.partido").match_one(item).text_content().strip()
        # Translate to English since being an Independent is a universal construct
        if party == "Independiente":
            party = "Independent"

        p = ScrapePerson(
            name=name,
            state="pr",
            chamber="upper",
            district="",
            party=party,
        )

        title = CSS("span.position").match_one(item).text_content().strip()
        if not re.search(r"{Position}", title):
            p.extras["title"] = title

        detail_link = CSS("a").match_one(item).get("href")

        p.add_source(self.source.url)
        p.add_source(detail_link)
        p.add_link(detail_link, note="homepage")

        return p


# class House(HtmlListPage):
#     source = URL("http://www.tucamarapr.org/dnncamara/ComposiciondelaCamara/Biografia.aspx")
#     selector = CSS("ul.list-article li")

#     def process_item(self, item):

# p = ScrapePerson(
#     name=name,
#     state="pr",
#     chamber="lower",
#     district=district,
#     party=party,
# )

# return p
