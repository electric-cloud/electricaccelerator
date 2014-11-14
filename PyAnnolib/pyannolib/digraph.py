"""Directed Acyclic Graph"""

import types

# Indices for the edge tuples
EDGE_LABEL = 0
EDGE_NODE = 1

class Node:
    def __init__(self, name):
        self.name = name

        # We keep track of edges going in
        # both directions, so that we can walk
        # the tree in both directions if we need to.
        # Items are tuples: (label, Node)
        #
        # I use "out" and "in" in the sense of the
        # way in which I usually draw DAGS for build systems.
        # Arrows pointing "out" refer to what we depend on.
        # That's backwards if you think if "out" as what
        # we produce. Deal with it. :)
        self.out_edges = [] # what we depend on
        self.in_edges = []  # what depends on us

    def get_name(self):
        return self.name

    def get_out_edges(self):
        return self.out_edges

    def get_in_edges(self):
        return self.in_edges

    def get_num_out_edges(self):
        return len(self.out_edges)

    def get_num_in_edges(self):
        return len(self.in_edges)

    def add_out_edge(self, label, other_node):
        return self.out_edges.append( (label, other_node) )

    def add_in_edge(self, label, other_node):
        return self.in_edges.append( (label, other_node) )

    def has_out_edge(self, label, other_node):
        return (label, other_node) in self.out_edges

    def has_in_edge(self, label, other_node):
        return (label, other_node) in self.in_edges


class DAG:
    """DAG with labeled edges"""

    def __init__(self):
        # Key = node name, Value = Node object
        self.nodes = {}

        # Nodes with no parents
        self.root_nodes = set()
        
        # Nodes with no children
        self.leaf_nodes = set()

    def get_leaf_nodes(self):
        return list(self.leaf_nodes)

    def get_root_nodes(self):
        return list(self.root_nodes)

    def get_node(self, name):
        return self.nodes.get(name)

    def add_node(self, name):
        """Create a new node and insert it into the DAG,
        with no connection. Raises ValueError if a node with
        that name already exists. Returns the new Node object."""
        assert type(name) == types.StringType

        if name in self.nodes:
            msg = "A node with name '%s' already exists" % (name,)
            raise ValueError(msg)

        new_node = self.nodes[name] = Node(name)

        # No connections means it is both a leaf and a root
        self.leaf_nodes.add(new_node)
        self.root_nodes.add(new_node)

        return new_node

    def set_node(self, name):
        """Return the node if it exists. If it doesn't exist,
        add it, and return the new node."""
        if name in self.nodes:
            return self.nodes[name]
        else:
            return self.add_node(name)

    def add_edge(self, node_a, edge_label, node_b):
        """Creates a new edge between two nodes. If that
        edge already exists, raises ValueError. Returns nothing."""
        # Does the edge already exists?
        if node_a.has_out_edge(edge_label, node_b):
            msg = "Node %s alrady has edge (%s, %s)" % \
                    (node_a.get_name(), edge_label, node_b.get_name())
            raise ValueError(msg)

        # There is no need to check node_b for its in-edges,
        # because our algorithm always sets both node_a/out and node_b/in

        # Add the edges to both nodes
        node_a.add_out_edge(edge_label, node_b)
        node_b.add_in_edge(edge_label, node_a)

        # Now that node_a has an out-edge, it cannot be a leaf node.
        if node_a.get_num_out_edges() == 1:
            self.leaf_nodes.remove(node_a)

        # Now that node_b has an in-edge, it cannot be a root node.
        if node_b.get_num_in_edges() == 1:
            self.root_nodes.remove(node_b)

    def set_edge(self, node_a, edge_label, node_b):
        """Creates the edge between two nodes. If that edge
        already exists, it's a no-op."""
        if node_a.has_out_edge(edge_label, node_b):
            return
        else:
            self.add_edge(node_a, edge_label, node_b)

