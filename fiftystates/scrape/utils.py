import os
import tempfile

def pdf_to_text(filename):
    (fd, temp_path) = tempfile.mkstemp()
    os.system("pdftotext %s %s" % (filename, temp_path))

    with os.fdopen(fd) as f:
        text = f.read()

    os.remove(temp_path)

    return text
