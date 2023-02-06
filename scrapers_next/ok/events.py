from spatula import URL, HtmlListPage, XPath
import time


class Events(HtmlListPage):
    source = URL(
        "https://www.okhouse.gov/calendars?start=2023-01-10&end=2023-03-31", timeout=120
    )
    time.sleep(120)
    selector = XPath(
        "/ html / body / div[1] / div / div[2] / div / main / div / div / div[2] / div"
    )

    def process_item(self, item):
        time.sleep(120)
        print(item)
        print(item.text)
        print([i for i in item.getchildren()])
        print([i for i in item.getchildren()][1].text)
        # print(item.text)


# CSS("div .flex .mb-4 > div > div > div")
# XPath('//*[@id="__next"]/div/div[2]/div/main/div/div/div[2]/div')
# __next > div > div.flex-grow.flex.flex-col > div > main > div > div > div.flex.flex-col.w-full.m-auto.max-w-\[832px\] > div > div:nth-child(2) > article > div > div.flex.mb-4 > div > div:nth-child(1) > div.flex-1 > div.capitalize.line-clamp-4 > h4
# __next > div > div.flex-grow.flex.flex-col > div > main > div > div > div.flex.flex-col.w-full.m-auto.max-w-\[832px\] > div > div) > article > div > div.flex.mb-4 > div > div > div.flex-1
