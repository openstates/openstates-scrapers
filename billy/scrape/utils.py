import subprocess
import os

def convert_word(filename, type='html'):
    command = "abiword -t %(filename)s.html %(filename)s; cat %(filename)s.html" % locals()    
    p = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, cwd="/tmp")
#    error = p.stderr.readlines()    
 #   if error:
#        raise Exception("".join(error))
    html = p.stdout.readlines()
    return "".join(html)

def convert_pdf(filename, type='xml'):
    commands = {'text': ['pdftotext', '-layout', filename, '-'],
                'text-nolayout': ['pdftotext', filename, '-'],
                'xml':  ['pdftohtml', '-xml', '-stdout', filename],
                'html': ['pdftohtml', '-stdout', filename]}
    pipe = subprocess.Popen(commands[type], stdout=subprocess.PIPE,
                            close_fds=True).stdout
    data = pipe.read()
    pipe.close()
    return data


def pdf_to_lxml(filename, type='html'):
    import lxml.html
    text = convert_pdf(filename, type)
    return lxml.html.fromstring(text)
