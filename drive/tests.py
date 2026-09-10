"""
Standard Django test discovery entrypoint.
Imports the 19 test cases from tests/test_unit.py so running `python manage.py test`
automatically discovers and executes all tests seamlessly.
"""
from tests.test_unit import *
