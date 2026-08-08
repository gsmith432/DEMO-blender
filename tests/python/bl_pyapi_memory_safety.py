# SPDX-FileCopyrightText: 2026 Blender Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""
Regression tests for Python API memory-safety fixes from !161562.

These paths previously crashed, read out of bounds, or used freed memory on
valid but uncommon call patterns. Coverage is intentionally narrow and
deterministic (no GPU backend init, no UI).

Usage:
  blender --background --factory-startup --python tests/python/bl_pyapi_memory_safety.py
"""
__all__ = (
    "main",
)

import gc
import unittest

import bmesh
import bpy
from gpu.types import GPUShaderCreateInfo
from mathutils import geometry


class TestTempDataContextManager(unittest.TestCase):
    """``bpy.data.temp_data`` must tolerate discard/misuse without crashing."""

    def test_discard_without_enter_does_not_crash(self):
        # PyObject_GC_New does not zero ``data_rna``; dealloc must tolerate nullptr.
        ctx = bpy.data.temp_data()
        del ctx
        gc.collect()

    def test_exit_without_enter_raises(self):
        ctx = bpy.data.temp_data()
        with self.assertRaises(RuntimeError):
            ctx.__exit__(None, None, None)

    def test_reenter_raises(self):
        ctx = bpy.data.temp_data()
        ctx.__enter__()
        with self.assertRaises(RuntimeError):
            ctx.__enter__()
        ctx.__exit__(None, None, None)

    def test_normal_enter_exit_still_works(self):
        with bpy.data.temp_data() as data:
            self.assertIsNotNone(data)
            mesh = data.meshes.new("TempCoverageMesh")
            self.assertEqual(mesh.name, "TempCoverageMesh")
        # Temporary Main is freed on exit; mesh must not remain in the real Main.
        self.assertIsNone(bpy.data.meshes.get("TempCoverageMesh"))


class TestDelaunay2dCdtFaces(unittest.TestCase):
    """``geometry.delaunay_2d_cdt`` face parsing must iterate face count, not flat size."""

    def test_multiple_faces_with_uneven_lengths(self):
        # Uneven face sizes make flattened length != face count, which triggered
        # the out-of-bounds read in mathutils_array_parse_alloc_viseq.
        verts = [
            (0.0, 0.0),
            (2.0, 0.0),
            (2.0, 2.0),
            (0.0, 2.0),
            (1.0, 1.0),
        ]
        faces = [
            [0, 1, 4],
            [1, 2, 4],
            [2, 3, 4],
            [3, 0, 4],
            [0, 1, 2, 3],
        ]
        out = geometry.delaunay_2d_cdt(verts, [], faces, 0, 1e-6, True)
        self.assertEqual(len(out), 6)
        out_verts, _edges, out_faces, *_ = out
        self.assertGreaterEqual(len(out_verts), 4)
        self.assertGreaterEqual(len(out_faces), 1)

    def test_empty_faces_with_edges(self):
        verts = [(0.0, 0.0), (1.0, 0.0), (0.0, 1.0)]
        edges = [(0, 1), (1, 2), (2, 0)]
        out = geometry.delaunay_2d_cdt(verts, edges, [], 0, 1e-6, True)
        self.assertEqual(len(out[0]), 3)


class TestBMeshOpsGetAttr(unittest.TestCase):
    """``getattr(bmesh.ops, name)`` must keep a stable static operator name."""

    def test_dynamic_name_lookup_and_call(self):
        # Construct the attribute name at runtime so it is not an interned
        # constant; the operator must not keep a pointer into a freed string.
        for _ in range(3):
            opname = "".join(("create_", "cube"))
            op = getattr(bmesh.ops, opname)
            bm = bmesh.new()
            try:
                op(bm, size=0.5)
                self.assertEqual(len(bm.verts), 8)
            finally:
                bm.free()
            del opname, op
            gc.collect()


class TestDriverVariableRename(unittest.TestCase):
    """Renaming driver variables must not free the active expr_comp tuple early."""

    def setUp(self):
        bpy.ops.wm.read_factory_settings(use_empty=False)
        self.obj = bpy.data.objects["Cube"]

    def test_rename_variable_then_evaluate(self):
        self.obj.driver_add("scale", 0)
        fcu = self.obj.animation_data.drivers[0]
        drv = fcu.driver
        drv.type = 'SCRIPTED'
        drv.expression = "var"

        var = drv.variables.new()
        var.name = "var"
        var.type = 'SINGLE_PROP'
        tgt = var.targets[0]
        tgt.id_type = 'SCENE'
        tgt.id = bpy.context.scene
        tgt.data_path = "frame_current"

        bpy.context.scene.frame_set(7)
        bpy.context.view_layer.update()
        self.assertAlmostEqual(self.obj.scale.x, 7.0, places=5)

        var.name = "renamed"
        drv.expression = "renamed"
        bpy.context.scene.frame_set(11)
        bpy.context.view_layer.update()
        gc.collect()
        self.assertAlmostEqual(self.obj.scale.x, 11.0, places=5)

        # A second rename after adding another variable rebuilds expr_vars again.
        var2 = drv.variables.new()
        var2.name = "extra"
        var2.type = 'SINGLE_PROP'
        tgt2 = var2.targets[0]
        tgt2.id_type = 'SCENE'
        tgt2.id = bpy.context.scene
        tgt2.data_path = "frame_current"

        var.name = "base"
        drv.expression = "base + extra"
        bpy.context.scene.frame_set(3)
        bpy.context.view_layer.update()
        gc.collect()
        self.assertAlmostEqual(self.obj.scale.x, 6.0, places=5)


class TestGPUShaderCreateInfoKeywordName(unittest.TestCase):
    """``name=`` keyword args must not index positional ``args`` out of bounds."""

    def test_push_constant_fragment_out_and_image_keywords(self):
        info = GPUShaderCreateInfo()
        # All three call sites previously used PyTuple_GET_ITEM(args, N) for the
        # name reference list when USE_GPU_PY_REFERENCES was enabled.
        info.push_constant(type='FLOAT', name='coverage_pc')
        info.fragment_out(slot=0, type='VEC4', name='coverage_frag')
        info.image(slot=0, format='RGBA8', type='FLOAT_2D', name='coverage_img')


def main():
    import sys
    sys.argv = [__file__] + (sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    unittest.main()


if __name__ == "__main__":
    main()
