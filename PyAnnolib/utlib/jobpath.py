# Copyright (c) 2013 by Cisco Systems, Inc.

import os
import unittest

from pyannolib import annolib
from utlib import util

class jobpathTests(unittest.TestCase):
    """Check the funcationaliby of jobpath"""

    @classmethod
    def setUpClass(cls):
        """Parse the file once, for this entire class"""
        annofile = os.path.join(util.UTFILES_DIR, "make-3.82-emake-7.0.0.xml")
        cls.build = annolib.AnnotatedBuild(annofile)

        # Collect all the jobs
        cls.jobs = cls.build.getAllJobs()

        cls.build.close()

    def find_job_for_target(self, target):
        return [j for j in self.jobs if j.getName() == target][0]

    def find_job_by_id(self, ID):
        return [j for j in self.jobs if j.getID() == ID][0]

    def test_dir(self):
        # Make #0
        # emake.................
        #
        # J0...012012f50
        # all
        #
        # Make #1
        # /auto/ecloud/emake-7.0.0/64/bin/emake all-recursive
        #
        # J0..012028170
        # all-recursive
        #
        # Make #6
        # /auto/ecloud/emake-7.0.0/64/bin/emake all-am
        #
        # J0...0120671b0
        # dir.o
        dir_job = self.find_job_for_target("dir.o")
        self.assertEqual(dir_job.getID(), "J00000000120671b0")

        make6 = dir_job.getMakeProcess()
        self.assertEqual(make6.getID(), "M00000006")

        all_recursive_job_id = make6.getParentJobID()
        self.assertEqual(all_recursive_job_id, "J0000000012028170")
        all_recursive_job = self.find_job_by_id(all_recursive_job_id)

        make1 = all_recursive_job.getMakeProcess()
        self.assertEqual(make1.getID(), "M00000001")

        all_job_id = make1.getParentJobID()
        self.assertEqual(all_job_id, "J0000000012012f50")
        all_job = self.find_job_by_id(all_job_id)

        make0 = all_job.getMakeProcess()
        self.assertEqual(make0.getID(), "M00000000")
