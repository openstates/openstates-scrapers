import subprocess

def convert_pdf(filename, type='xml'):
    commands = {'text': ['pdftotext', '-layout', filename, '-'],
                'xml':  ['pdftohtml', '-xml', '-stdout', filename],
                'html': ['pdftohtml', '-stdout', filename]}
    pipe = subprocess.Popen(commands[type], stdout=subprocess.PIPE).stdout
    return pipe.read()

def pdf_to_lxml(filename, type='html'):
    import lxml.html
    text = convert_pdf(filename, type)
    return lxml.html.fromstring(text)
