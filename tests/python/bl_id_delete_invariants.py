# SPDX-FileCopyrightText: 2026 Blender Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Regression: batch ID delete must refresh Main invariants.

Production-only fix (``lib_id_delete.cc``): after ``batch_remove`` of many
node groups, ``BKE_main_ensure_invariants`` must run so the next depsgraph
rebuild/evaluation does not assert or hang.

# ./blender.bin --background --factory-startup \\
#   --python tests/python/bl_id_delete_invariants.py -- --verbose
"""

__all__ = (
    "main",
)

import unittest

import bpy


def _new_passthrough_geometry_group(name: str) -> bpy.types.NodeTree:
    ng = bpy.data.node_groups.new(name, 'GeometryNodeTree')
    ng.interface.new_socket("Geometry", in_out='INPUT', socket_type='NodeSocketGeometry')
    ng.interface.new_socket("Geometry", in_out='OUTPUT', socket_type='NodeSocketGeometry')
    group_in = ng.nodes.new("NodeGroupInput")
    group_out = ng.nodes.new("NodeGroupOutput")
    ng.links.new(group_in.outputs[0], group_out.inputs[0])
    return ng


class TestBatchDeleteMainInvariants(unittest.TestCase):
    def setUp(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)

    def test_batch_remove_node_groups_then_depsgraph_update(self):
        groups = [_new_passthrough_geometry_group(f"BatchDeleteGroup{i}") for i in range(24)]

        # Nested reference: outer group instances an inner group.
        outer = groups[0]
        inner = groups[1]
        group_node = outer.nodes.new("GeometryNodeGroup")
        group_node.node_tree = inner

        mesh = bpy.data.meshes.new("BatchDeleteMesh")
        mesh.from_pydata([(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)], [], [(0, 1, 2)])
        obj = bpy.data.objects.new("BatchDeleteObject", mesh)
        bpy.context.scene.collection.objects.link(obj)
        modifier = obj.modifiers.new("GeometryNodes", 'NODES')
        modifier.node_group = outer

        bpy.data.batch_remove(list(groups))
        self.assertEqual(len(bpy.data.node_groups), 0)
        self.assertIsNone(modifier.node_group)

        # These are the post-delete steps that used to assert/freeze without
        # BKE_main_ensure_invariants after batch ID deletion.
        bpy.context.view_layer.update()
        depsgraph = bpy.context.evaluated_depsgraph_get()
        evaluated = obj.evaluated_get(depsgraph)
        self.assertIsNotNone(evaluated)
        self.assertEqual(evaluated.type, 'MESH')
        self.assertEqual(len(evaluated.data.polygons), 1)


def main():
    import sys
    sys.argv = [__file__] + (sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    unittest.main()


if __name__ == "__main__":
    main()
