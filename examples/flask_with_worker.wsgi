import os
import sys

sys.path.insert(0, os.path.split(os.path.abspath(__file__))[0])

from flask_with_worker import app as application
