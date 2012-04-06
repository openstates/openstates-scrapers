def fl_handler(filedata, metadata):

    # check for beginning of tag, MS throws in some xmlns stuff
    if '<html' not in filedata:
        return ''

    doc = lxml.html.fromstring(filedata)
    if metadata['chamber'] == 'lower':
        # 2nd column of the table has all of the good stuff, first is line #
        return ' '.join(x.text_content() for x in doc.xpath('//tr/td[2]'))
    else:
        text = doc.xpath('//pre')[0].text_content()
        return text_after_line_numbers(text.splitlines())


def pa_handler(filedata, metadata):
    doc = lxml.html.fromstring(filedata)
    # another state where the second column of the table is the good stuff
    text = ' '.join(x.text_content() for x in doc.xpath('//tr/td[2]'))
    return collapse_spaces(text)


def oh_handler(filedata, metadata):
    doc = lxml.html.fromstring(filedata)
    # left-aligned columns
    text = ' '.join(x.text_content() for x in doc.xpath('//td[@align="LEFT"]'))
    return collapse_spaces(text)


def mi_handler(filedata, metadata):
    # no real pattern here, just grab the text from the body
    doc = lxml.html.fromstring(filedata)
    return collapse_spaces(doc.xpath('//body')[0].text_content())


def nc_handler(filedata, metadata):
    doc = lxml.html.fromstring(filedata)
    # all content has a class that starts with a (aSection, aTitle, etc)
    text = ' '.join([x.text_content() for x in
                     doc.xpath('//p[starts-with(@class, "a")]')])
    return collapse_spaces(text)


def nj_handler(filedata, metadata):
    if metadata['filename'].endswith('.WPD'):
        return ''
    else:
        doc = lxml.html.fromstring(filedata)
        text = doc.xpath('//div[@class="Section3"]')[0].text_content()
        return collapse_spaces(text)


def va_handler(filedata, metadata):
    doc = lxml.html.fromstring(filedata)
    text = ' '.join(x.text_content()
                    for x in doc.xpath('//div[@id="mainC"]/p'))
    return collapse_spaces(text)


def wa_handler(filedata, metadata):
    doc = lxml.html.fromstring(filedata)
    text = '\n'.join(collapse_spaces(x.text_content()) for x in
                     doc.xpath('//body/p'))
    return text


def wv_handler(filedata, metadata):
    doc = lxml.html.fromstring(filedata)
    return doc.xpath('//div[@id="blocktext"]')[0].text_content()
