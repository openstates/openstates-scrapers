import os
import urllib
import tempfile
import pycurl
import subprocess

urla='http://www.oslpr.org/files/docs/%7B1F4D2323-1229-4EBA-BC06-F364AF97303F%7D.doc'
#extract from url the last part where the file name is with the extension
def get_filename_parts_from_url(url):
    fullname = url.split('/')[-1].split('#')[0].split('?')[0]
    t = list(os.path.splitext(fullname))
    if t[1]:
        t[1] = t[1][1:]
    return t

#pass unquoted url to this funcion and it will download the .doc file
def retrieve(url):
    filename1, extension = get_filename_parts_from_url(url)
    filename=filename1+'.'+extension
    f = open("/tmp/"+filename, 'wb')
    c = pycurl.Curl()
    c.setopt(pycurl.URL, str(url))
    c.setopt(pycurl.WRITEFUNCTION, f.write)
    try:
        c.perform()
    except:
        filename = None
    finally:
        c.close()
        f.close()
    return filename1

#convert .doc to html
def document_to_html(file_path):
    tmp = "/tmp"
    #check extension that it's not pdf
    name_guid = file_path
#    if '.pdf' == name_guid :
	    #warning("Pdf file found on file")
    # convert the file, using a temporary file with the same filename
    command = "abiword -t %(tmp)s/%(name_guid)s.html %(file_path)s.doc; cat %(tmp)s/%(name_guid)s.html" % locals()
    print command
    p = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, cwd=tmp)
    stdout_value, stderr_value = p.communicate();
    if stderr_value:
        raise Exception("".join(error))
    html = stdout_value
    return "".join(html)

#downlad doc and convert to htm
def wget_doc(url_path):
	print(document_to_html(retrieve(urllib.unquote(url_path))))

wget_doc(urla)
