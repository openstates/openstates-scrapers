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
