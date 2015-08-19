# Copyright (c) 2015 by Gilbert Ramirez <gram@alumni.rice.edu>

import os
import unittest

from pyannolib import annolib
from utlib import util

class Emake8Tests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """Parse the file once, for this entire class"""
        annofile = os.path.join(util.UTFILES_DIR, "emake8.xml")
        cls.build = annolib.AnnotatedBuild(annofile)

        # Collect all the jobs (so that we have the metrics)
        cls.jobs = cls.build.getAllJobs()

        cls.build.close()

    def test_commit(self):
        commitTimes = self.jobs[0].getCommitTimes()
        self.assertEqual(commitTimes.getStart(), "4.048628")
        self.assertEqual(commitTimes.getWait(), "4.048629")
        self.assertEqual(commitTimes.getCommit(), "4.048635")
        self.assertEqual(commitTimes.getWrite(), "4.058635")

