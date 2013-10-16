# Copyright (c) 2013 by Cisco Systems, Inc.

import os
import unittest

from pyannolib import annolib
from utlib import util

class buildTests(unittest.TestCase):
    """Check attributes of the Build class."""

    @classmethod
    def setUpClass(cls):
        """Parse the file once, for this entire class"""
        annofile = os.path.join(util.UTFILES_DIR, "make-3.82-emake-5.3.0.xml")
        cls.build = annolib.AnnotatedBuild(annofile)

        # Collect all the jobs (so that we have the metrics)
        cls.jobs = cls.build.getAllJobs()

        cls.build.close()

    def test_attributes(self):
        # Test the attributes of the Build record
        self.assertEqual(self.build.getBuildID(), "219798")
        self.assertEqual(self.build.getCM(), "sjc-buildcm2:8030")
        self.assertEqual(self.build.getStart(),
                "Fri 11 Jan 2013 10:14:59 AM PST")

    def test_properties(self):
        props = self.build.getProperties()

        # First property
        cmdline = "/sw/licensed/ecloud/latest/64/bin/emake --emake-cm=sjc-buildcm2 --emake-build-label=EC_EMAKE --emake-annodetail=file,history,waiting --emake-history=create --emake-root=/ws/gilramir-sjc/prj/make-3.82 --emake-resource=sjc-cel-5.03-x86-64"
        self.assertEqual(props["CommandLine"], cmdline)

        # Something from the middle
        self.assertEqual(props["CWD"], "/ws/gilramir-sjc/prj/make-3.82")

        # Last property
        self.assertEqual(props["AnnoDetail"],
                "basic,file,history,waiting")

    def test_variables(self):
        vars = self.build.getVars()

        # First env var
        self.assertEqual(vars["CCACHE_DIR"], "/auto/ccache")

        # Something from the middle
        self.assertEqual(vars["EDITOR"], "vim")

        # Last env var (plus, it's multi-line!)
        rmview = """() {  VIEW=$(ct pwv | grep 'Working directory view' | awk '{print $4;}');
 if [ "$VIEW" != '**' ]; then
 cd ~;
 echo Removing $VIEW;
 cc_rmview -force -view "$VIEW" -vob /vob/ios;
 fi
}"""
        self.assertEqual(vars["rmview"], rmview)

    def test_metrics(self):
        metrics = self.build.getMetrics()

        # First metric
        self.assertEqual(metrics["terminated"], "266")
        
        # Something in the middle
        self.assertEqual(metrics["elapsed"], "3.539654")

        # Last metric
