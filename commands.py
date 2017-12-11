import os
import sys

if 'tangled' not in sys.modules:
    sys.path.insert(0, os.path.abspath('../tangled'))

from tangled.commands import *
