# Copyright (c) 2014 by Cisco Systems, Inc.

import unittest

from tyrannolib import digraph

class DAGTests(unittest.TestCase):
    """Check the DAG logic."""

    def test_empty(self):
        #
        # Test the getters on an empty DAG
        #
        dag = digraph.DAG()

        self.assertEqual([], dag.get_leaf_nodes())
        self.assertEqual([], dag.get_root_nodes())
        self.assertEqual(None, dag.get_node("no-such-node"))

    def test_one_node(self):
        #
        # Test the getters on a DAG with one node
        #
        dag = digraph.DAG()

        name = "foo"
        node = dag.add_node(name)

        self.assertEqual(node.get_name(), name)

        self.assertEqual([node], dag.get_leaf_nodes())
        self.assertEqual([node], dag.get_root_nodes())
        self.assertEqual(node, dag.get_node(name))

    def test_one_edge(self):
        #
        # Test the getters on a DAG of two nodes and one edge
        #
        dag = digraph.DAG()

        name_a = "a"
        node_a = dag.add_node(name_a)

        name_b = "b"
        node_b = dag.add_node(name_b)

        # Connect them, a->b
        edge_label = "USES"
        dag.add_edge(node_a, edge_label, node_b)

        self.assertEqual([node_b], dag.get_leaf_nodes())
        self.assertEqual([node_a], dag.get_root_nodes())

        # Check a's edges
        self.assertEqual([(edge_label, node_b)], node_a.get_out_edges())
        self.assertEqual([], node_a.get_in_edges())

        # Check b's edges
        self.assertEqual([], node_b.get_out_edges())
        self.assertEqual([(edge_label, node_a)], node_b.get_in_edges())

    def test_dup_node(self):
        #
        # Test that the DAG won't let us enter duplicate nodes
        #
        dag = digraph.DAG()

        name = "foo"
        node = dag.add_node(name)

        self.assertEqual(node.get_name(), name)

        with self.assertRaises(ValueError):
            dag.add_node(name)

    def test_dup_edge(self):
        #
        # Test that the DAG won't let us enter duplicate edges
        #
        dag = digraph.DAG()

        name_a = "a"
        node_a = dag.add_node(name_a)

        name_b = "b"
        node_b = dag.add_node(name_b)

        # Connect them, a->b
        edge_label = "USES"
        dag.add_edge(node_a, edge_label, node_b)

        self.assertEqual([node_b], dag.get_leaf_nodes())
        self.assertEqual([node_a], dag.get_root_nodes())

        with self.assertRaises(ValueError):
            dag.add_edge(node_a, edge_label, node_b)
