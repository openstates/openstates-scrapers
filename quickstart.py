# imports we'll use in this example
from spatula import HtmlPage, HtmlListPage, CSS, XPath, SelectorError


class EmployeeList(HtmlListPage):
    # by providing this here, it can be omitted on the command line
    # useful in cases where the scraper is only meant for one page
    source = "https://scrapple.fly.dev/staff"

    # each row represents an employee
    selector = CSS("#employees tbody tr")

    def process_item(self, item):
        # this function is called for each <tr> we get from the selector
        # we know there are 4 <tds>
        first, last, position, details = item.getchildren()
        return EmployeeDetail(
            dict(
                first=first.text,
                last=last.text,
                position=position.text,
            ),
            source=XPath("./a/@href").match_one(details),
        )


class EmployeeDetail(HtmlPage):
    def process_page(self):
        status = CSS("#status").match_one(self.root)
        hired = CSS("#hired").match_one(self.root)
        return dict(
            status=status.text,
            hired=hired.text,
            # self.input is the data passed in from the prior scrape,
            # in this case a dict we can expand here
            **self.input,
        )
