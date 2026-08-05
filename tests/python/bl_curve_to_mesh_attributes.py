# SPDX-FileCopyrightText: 2026 Blender Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Regression: curve -> mesh must not propagate mesh topology attribute names.

Fix #161793: CurvesGeometry can carry attributes whose names collide with mesh
builtins (``.edge_verts``, ``.corner_vert``, ``.corner_edge``). Propagating them
as generic attributes corrupts mesh topology. Conversion must skip those names
while still transferring ordinary attributes.

# ./blender.bin --background --factory-startup \\
#   --python tests/python/bl_curve_to_mesh_attributes.py -- --verbose
"""

__all__ = (
    "main",
)

import unittest

import bpy


MESH_TOPOLOGY_ATTRS = (".edge_verts", ".corner_vert", ".corner_edge")


class TestCurveToMeshBuiltinAttributeFilter(unittest.TestCase):
    def setUp(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)

    def _curves_object_with_collision_attrs(self):
        curves = bpy.data.hair_curves.new("CurveBuiltinClash")
        curves.add_curves([4])
        for i, point in enumerate(curves.points):
            point.position = (float(i), 0.0, 0.0)

        for name in MESH_TOPOLOGY_ATTRS:
            attr = curves.attributes.new(name, 'FLOAT', 'POINT')
            for i in range(len(attr.data)):
                attr.data[i].value = 123.0 + float(i)

        custom = curves.attributes.new("my_attr", 'FLOAT', 'POINT')
        for i in range(len(custom.data)):
            custom.data[i].value = 7.0 + float(i)

        obj = bpy.data.objects.new("CurveBuiltinClash", curves)
        bpy.context.scene.collection.objects.link(obj)
        bpy.context.view_layer.objects.active = obj
        obj.select_set(True)
        return obj

    def test_convert_skips_mesh_topology_names(self):
        obj = self._curves_object_with_collision_attrs()
        bpy.ops.object.convert(target='MESH')

        self.assertEqual(obj.type, 'MESH')
        mesh = obj.data
        self.assertGreater(len(mesh.edges), 0)

        edge_verts = mesh.attributes[".edge_verts"]
        self.assertEqual(edge_verts.data_type, 'INT32_2D')
        self.assertEqual(edge_verts.domain, 'EDGE')
        self.assertTrue(edge_verts.is_internal)

        # Topology values must remain vertex indices, not the FLOAT 123+i payload.
        flat = [0] * (len(edge_verts.data) * 2)
        edge_verts.data.foreach_get("value", flat)
        self.assertTrue(all(0 <= v < len(mesh.vertices) for v in flat))
        self.assertFalse(any(abs(float(v) - 123.0) < 1e-3 for v in flat))

        for name in (".corner_vert", ".corner_edge"):
            attr = mesh.attributes[name]
            self.assertIn(attr.data_type, {'INT', 'INT32'})
            self.assertEqual(attr.domain, 'CORNER')
            self.assertTrue(attr.is_internal)

        self.assertIn("my_attr", mesh.attributes)
        my_attr = mesh.attributes["my_attr"]
        self.assertEqual(my_attr.data_type, 'FLOAT')
        self.assertEqual(my_attr.domain, 'POINT')
        self.assertFalse(my_attr.is_internal)


def main():
    import sys
    sys.argv = [__file__] + (sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    unittest.main()


if __name__ == "__main__":
    main()
