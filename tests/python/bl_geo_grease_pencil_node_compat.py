# SPDX-FileCopyrightText: 2026 Blender Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Regression tests for Grease Pencil geometry-node RNA compatibility accessors.

These deprecated RNA properties mirror menu socket defaults so older scripts and
forward-compat write paths keep working after node_rna storage was removed.
"""

import unittest
import warnings

import bpy


def _new_geometry_tree(name: str):
    tree = bpy.data.node_groups.new(name, "GeometryNodeTree")
    tree.is_modifier = True
    return tree


class TestGreasePencilNodeCompat(unittest.TestCase):
    def setUp(self):
        self.tree = _new_geometry_tree("TestGPCompat")

    def tearDown(self):
        bpy.data.node_groups.remove(self.tree)

    def test_merge_layers_mode_syncs_with_socket(self):
        node = self.tree.nodes.new("GeometryNodeMergeLayers")
        mode_socket = node.inputs["Mode"]

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always", DeprecationWarning)
            self.assertEqual(node.mode, "MERGE_BY_NAME")
            self.assertEqual(mode_socket.default_value, "By Name")

            node.mode = "MERGE_BY_ID"
            self.assertEqual(node.mode, "MERGE_BY_ID")
            self.assertEqual(mode_socket.default_value, "By Group ID")

            mode_socket.default_value = "By Name"
            self.assertEqual(node.mode, "MERGE_BY_NAME")

        self.assertTrue(any(issubclass(w.category, DeprecationWarning) for w in caught))

    def test_set_grease_pencil_color_mode_syncs_with_socket(self):
        node = self.tree.nodes.new("GeometryNodeSetGreasePencilColor")
        mode_socket = node.inputs["Mode"]

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always", DeprecationWarning)
            self.assertEqual(node.mode, "STROKE")
            self.assertEqual(mode_socket.default_value, "Stroke")

            node.mode = "FILL"
            self.assertEqual(node.mode, "FILL")
            self.assertEqual(mode_socket.default_value, "Fill")

            mode_socket.default_value = "Stroke"
            self.assertEqual(node.mode, "STROKE")

        self.assertTrue(any(issubclass(w.category, DeprecationWarning) for w in caught))

    def test_set_grease_pencil_depth_order_syncs_with_socket(self):
        node = self.tree.nodes.new("GeometryNodeSetGreasePencilDepth")
        depth_socket = node.inputs["Depth Order"]

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always", DeprecationWarning)
            self.assertEqual(node.depth_order, "2D")
            self.assertEqual(depth_socket.default_value, "2D Layers")

            node.depth_order = "3D"
            self.assertEqual(node.depth_order, "3D")
            self.assertEqual(depth_socket.default_value, "3D Location")

            depth_socket.default_value = "2D Layers"
            self.assertEqual(node.depth_order, "2D")

        self.assertTrue(any(issubclass(w.category, DeprecationWarning) for w in caught))


if __name__ == "__main__":
    import sys
    sys.argv = [__file__] + (sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    unittest.main()
