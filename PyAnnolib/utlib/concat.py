# Copyright (c) 2014 by Cisco Systems, Inc.

import os
import unittest

from pyannolib import annolib
from utlib import util

class ConcatTests(unittest.TestCase):
    """Test the ConcatenatedFile class."""

    full_string = "ABCDEFGHIJKLMNOPQRSTUVWXYZ123456789"

    @classmethod
    def setUpClass(cls):
        first_filename = os.path.join(util.UTFILES_DIR, "concat.txt")
        cls.fh = annolib.anno_open(first_filename, "r")

    @classmethod
    def tearDownClass(cls):
        cls.fh.close()

    def test_read_all(self):
        #
        # Test that one read() reads the entire string.
        #
        self.fh.seek(0)
        data = self.fh.read()
        self.assertEqual(data, self.full_string)

    def test_read_N(self):
        #
        # Test that one read() reads the entire string.
        #
        self.fh.seek(0)
        data = self.fh.read(10)
        self.assertEqual(data, "ABCDEFGHIJ")

    def test_seek_set(self):
        #
        # Test that one read() reads the entire string.
        #
        self.fh.seek(26)
        data = self.fh.read()
        self.assertEqual(data, "123456789")

    def test_seek_cur(self):
        #
        # Test that one read() reads the entire string.
        #
        self.fh.seek(10, os.SEEK_CUR)
        self.fh.seek(16, os.SEEK_CUR)
        data = self.fh.read()
        self.assertEqual(data, "123456789")

    def test_seek_end(self):
        #
        # Test that one read() reads the entire string.
        #
        self.fh.seek(-34, os.SEEK_END)
        data = self.fh.read(8)
        self.assertEqual(data, "BCDEFGHI")
