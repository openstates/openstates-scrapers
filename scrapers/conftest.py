import os
import sys

# scrapers import each other as top-level packages (utils, il, ...), as os-update does
sys.path.insert(0, os.path.dirname(__file__))
