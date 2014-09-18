# Copyright (c) 2014 by Cisco Systems, Inc.

import unittest
from pyannolib import sequencing

class SeqTests(unittest.TestCase):
    """Check the sequencing algorithms.

    REMEMBER: timing tuples are (COMPLETED, INVOKED), so the
    bigger number is first, and the smaller number is second.
    """

    def _test_insertion(self, orig, new_frag, expected):
        agent = sequencing.Agent()
        agent.fragments = orig
        agent.addTimingTuple(new_frag[sequencing.INVOKED],
                new_frag[sequencing.COMPLETED])

        self.assertEqual(expected, agent.fragments)

    def test_catch_time_travel(self):
        orig     = []
        new_frag = (1.0, 2.0) # Completed is earlier than Invoked
        expected = []

        with self.assertRaises(sequencing.SequencingError):
            self._test_insertion(orig, new_frag, expected)

    def test_insert_first(self):
        orig     = []
        new_frag = (2.0, 1.0)
        expected = [ (2.0, 1.0) ]

        self._test_insertion(orig, new_frag, expected)


    def test_insert_before_no_overlap(self):
        orig     = [ (2.0, 1.0) ]
        new_frag = (3.0, 2.5)
        expected = [ (3.0, 2.5), (2.0, 1.0) ]

        self._test_insertion(orig, new_frag, expected)

    def test_insert_before_with_overlap(self):
        orig     = [ (2.0, 1.0) ]
        new_frag = (3.0, 1.5)
        expected = [ (3.0, 1.5), (2.0, 1.0) ]

        self._test_insertion(orig, new_frag, expected)

    def test_insert_after_no_overlap(self):
        orig     = [ (2.0, 1.0) ]
        new_frag = (0.9, 0.1)
        expected = [ (2.0, 1.0), (0.9, 0.1) ]

        self._test_insertion(orig, new_frag, expected)

    def test_insert_after_with_overlap(self):
        orig     = [ (2.0, 1.0) ]
        new_frag = (1.5, 0.1)
        expected = [ (2.0, 1.0), (1.5, 0.1) ]

        self._test_insertion(orig, new_frag, expected)

    def test_insert_middle_in_gap(self):
        orig     = [ (5.0, 4.0), (1.0, 0.0) ]
        new_frag = (3.0, 2.0)
        expected = [ (5.0, 4.0), (3.0, 2.0), (1.0, 0.0)]

        self._test_insertion(orig, new_frag, expected)

    def test_insert_middle_left_overlap(self):
        orig     = [ (5.0, 4.0), (1.0, 0.0) ]
        new_frag = (4.5, 2.0)
        expected = [ (5.0, 4.0), (4.5, 2.0), (1.0, 0.0)]

        self._test_insertion(orig, new_frag, expected)

    def test_insert_middle_right_overlap(self):
        orig     = [ (5.0, 4.0), (1.0, 0.0) ]
        new_frag = (3.0, 0.5)
        expected = [ (5.0, 4.0), (3.0, 0.5), (1.0, 0.0)]

        self._test_insertion(orig, new_frag, expected)


    def _test_merge(self, orig, expected):
        agent = sequencing.Agent()
        agent.fragments = orig
        agent.mergeOverlaps()

        self.assertEqual(expected, agent.fragments)

    def test_merge_no_change(self):
        orig     = [ (5.0, 4.0), (3.0, 2.0), (1.0, 0.0)]
        expected = [ (5.0, 4.0), (3.0, 2.0), (1.0, 0.0)]

        self._test_merge(orig, expected)

    def test_merge_one_right(self):
        orig     = [ (5.0, 4.0), (3.0, 0.5), (1.0, 0.0)]
        expected = [ (5.0, 4.0), (3.0, 0.0)]

        self._test_merge(orig, expected)

    def test_merge_one_left(self):
        orig     = [ (5.0, 4.0), (4.5, 2.0), (1.0, 0.0)]
        expected = [ (5.0, 2.0), (1.0, 0.0)]

        self._test_merge(orig, expected)

    def test_merge_three_chained(self):
        # The two tuples on the left overlap
        # The two tuples on the right overlap
        # But the first and last tuples do not overlap
        orig     = [ (5.0, 4.0), (4.5, 0.5), (1.0, 0.0)]
        expected = [ (5.0, 0.0)]

        self._test_merge(orig, expected)

    def test_merge_three_all_overlap(self):
        # Three tuples overlap with each other
        # Including the first and last (with each other)
        orig     = [ (5.0, 4.0), (4.9, 3.9), (4.1, 3.0)]
        expected = [ (5.0, 3.0)]

        self._test_merge(orig, expected)
