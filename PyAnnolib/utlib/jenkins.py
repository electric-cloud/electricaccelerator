# Copyright (c) 2013 by Cisco Systems, Inc.

import os
import sys
import unittest

from utlib import util

# This zip file name ot use for JUnitXML
JUNITXML_ZIP = "junitxml-0.6.zip"

# Has the sys.path been configured?
sys_path_configured = False

def setup_sys_path():
    global sys_path_configured
    if not sys_path_configured:
        # Add the JUnitXML zip package to sys.path so we can import
        # the junitxml library
        zip_file = os.path.join(util.DISTRO_DIR, "utlib", JUNITXML_ZIP)
        sys.path.append(zip_file)
        sys_path_configured = True

def main(top_name, report_name):
    """A unittest main() routine to be used when running under Jenkins."""
    setup_sys_path()

    import junitxml

    try:
        outfh = open(report_name, "w")
    except IOError, e:
        sys.exit("Could not write to %s : %s" % (report_name, e))

    # Create the object which will produce the JUnitXML output
    result = junitxml.JUnitXmlResult(outfh)
    result.startTestRun()

    # Have the test loader find tests in the module that was passed
    suite = unittest.TestLoader().loadTestsFromModule(sys.modules[top_name])
    suite.run(result)
    result.stopTestRun()
