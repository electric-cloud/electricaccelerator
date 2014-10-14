# Copyright (c) 2013 by Cisco Systems, Inc.

import os
import unittest

from pyannolib import annolib
from utlib import util

class JobPathTests(unittest.TestCase):
    """Check the funcationality of jobpath"""

    @classmethod
    def setUpClass(cls):
        """Parse the file once, for this entire class"""
        annofile = os.path.join(util.UTFILES_DIR, "make-3.82-emake-7.0.0.xml")
        cls.build = annolib.AnnotatedBuild(annofile)

        # Collect all the jobs
        cls.jobs = { job.getID() : job for job in cls.build.getAllJobs() }

        cls.build.close()

    def test_leaf_job(self):
        # This job is the link of the 'make' executable
        job  = self.jobs["J0000000012067840"]

        job_path = [obj.getID() for obj in self.build.getJobPath(job)]

        expected = ["M00000000", "J0000000012012f50",
                    "M00000001", "J0000000012028170",
                    "M00000006", "J0000000012067840"]

        self.assertEqual(job_path, expected)

    def test_parse_job(self):
        # This job is the leaf Make process (parse job)
        job = self.jobs["J000000001207d140"]

        job_path = [obj.getID() for obj in self.build.getJobPath(job)]

        expected = ["M00000000", "J0000000012012f50",
                    "M00000001", "J0000000012028170",
                    "M00000006", "J000000001207d140"]

        self.assertEqual(job_path, expected)


    def test_submake_job(self):
        # This job is the submake of 'all-recursive'
        # It is a rule job
        job = self.jobs["J0000000012012f50"]

        job_path = [obj.getID() for obj in self.build.getJobPath(job)]

        expected = ["M00000000", "J0000000012012f50"]

        self.assertEqual(job_path, expected)
