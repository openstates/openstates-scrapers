#!/usr/bin/env python

if __name__ == '__main__':
    import webbrowser
    import os

    path = "file:///" + os.path.abspath(os.path.join(os.path.dirname(__file__),
                                                     "browse.html"))
    webbrowser.get("firefox").open(path, new=2)
