# SPDX-FileCopyrightText: 2026 Blender Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""
Regression tests for Grease Pencil geometry-node RNA compatibility accessors.

These deprecated node properties must stay synchronized with their menu sockets
so older scripts and forward-compat write paths keep working after the socket
migration (see Geometry Nodes Grease Pencil compatibility fix).

blender --background --factory-startup --python tests/python/bl_geo_grease_pencil_node_compat.py
"""

__all__ = (
    "main",
)

import unittest
import warnings

import bpy


def _new_geometry_tree(name: str):
    nt = bpy.data.node_groups.new(name, "GeometryNodeTree")
    nt.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    nt.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    return nt


class TestGreasePencilNodeCompat(unittest.TestCase):
    def setUp(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        # Deprecated properties emit DeprecationWarning; ignore so the suite
        # focuses on behavioral sync rather than warning noise.
        warnings.simplefilter("ignore", DeprecationWarning)

    def test_merge_layers_mode_sync(self):
        nt = _new_geometry_tree("MergeLayersCompat")
        node = nt.nodes.new("GeometryNodeMergeLayers")
        mode_socket = node.inputs["Mode"]

        node.mode = "MERGE_BY_ID"
        self.assertEqual(node.mode, "MERGE_BY_ID")
        self.assertEqual(mode_socket.default_value, "By Group ID")

        mode_socket.default_value = "By Name"
        self.assertEqual(node.mode, "MERGE_BY_NAME")
        self.assertEqual(mode_socket.default_value, "By Name")

    def test_set_grease_pencil_color_mode_sync(self):
        nt = _new_geometry_tree("SetGPColorCompat")
        node = nt.nodes.new("GeometryNodeSetGreasePencilColor")
        mode_socket = node.inputs["Mode"]

        node.mode = "FILL"
        self.assertEqual(node.mode, "FILL")
        self.assertEqual(mode_socket.default_value, "Fill")

        mode_socket.default_value = "Stroke"
        self.assertEqual(node.mode, "STROKE")
        self.assertEqual(mode_socket.default_value, "Stroke")

    def test_set_grease_pencil_depth_order_sync(self):
        nt = _new_geometry_tree("SetGPDepthCompat")
        node = nt.nodes.new("GeometryNodeSetGreasePencilDepth")
        depth_socket = node.inputs["Depth Order"]

        node.depth_order = "3D"
        self.assertEqual(node.depth_order, "3D")
        self.assertEqual(depth_socket.default_value, "3D Location")

        depth_socket.default_value = "2D Layers"
        self.assertEqual(node.depth_order, "2D")
        self.assertEqual(depth_socket.default_value, "2D Layers")


def main():
    import sys
    sys.argv = [__file__] + (sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    unittest.main()


if __name__ == "__main__":
    main()
