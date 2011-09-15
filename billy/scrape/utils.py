import subprocess

def convert_pdf(filename, type='xml'):
    commands = {'text': ['pdftotext', '-layout', filename, '-'],
                'text-nolayout': ['pdftotext', filename, '-'],
                'xml':  ['pdftohtml', '-xml', '-stdout', filename],
                'html': ['pdftohtml', '-stdout', filename]}
    try:
        pipe = subprocess.Popen(commands[type], stdout=subprocess.PIPE,
                                close_fds=True).stdout
    except OSError:
        raise EnvironmentError("error running %s, missing executable?" %
                               ' '.join(commands[type]))
    data = pipe.read()
    pipe.close()
    return data


def pdf_to_lxml(filename, type='html'):
    import lxml.html
    text = convert_pdf(filename, type)
    return lxml.html.fromstring(text)
