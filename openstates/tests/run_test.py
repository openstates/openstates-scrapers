# Run all the tests with the data in the testdata directory.

import os
import sys
sys.path.append('.')
from openstates.tests.all_tests import main
sys.exit(main(os.path.abspath('testdata')))


