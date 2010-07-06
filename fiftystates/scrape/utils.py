import os
import tempfile
import subprocess

def pdf_to_text(filename):
    (fd, temp_path) = tempfile.mkstemp()
    os.system("pdftotext %s %s" % (filename, temp_path))

    with os.fdopen(fd) as f:
        text = f.read()

    os.remove(temp_path)

    return text

def pdf_to_html(filename):
    pipe = subprocess.Popen(["pdftohtml", "-stdout", filename],
                            stdout=subprocess.PIPE).stdout
    return pipe.read()

def pdf_to_lxml(filename):
    import lxml.html
    text = pdf_to_html(filename)
    return lxml.html.fromstring(text)
