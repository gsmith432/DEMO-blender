# SPDX-FileCopyrightText: 2026 Blender Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""
Regression tests for Python context managers that previously crashed when
misused (exit without enter, double exit, re-enter).

Covers production fixes from !161723:
- ``bpy.data.libraries.load``
- ``blf.bind_imbuf``

Usage:
  blender --background --factory-startup --python tests/python/bl_pyapi_context_managers.py
"""
__all__ = (
    "main",
)

import os
import shutil
import tempfile
import unittest

import blf
import bpy
import imbuf


class TestLibrariesLoadContextManager(unittest.TestCase):
    """``bpy.data.libraries.load`` must not use uninitialized state on misuse."""

    @classmethod
    def setUpClass(cls):
        cls._tmpdir = tempfile.mkdtemp(prefix="bl_pyapi_lib_ctx_")
        cls._libpath = os.path.join(cls._tmpdir, "lib.blend")
        bpy.ops.wm.read_factory_settings(use_empty=False)
        bpy.ops.wm.save_as_mainfile(filepath=cls._libpath, check_existing=False)
        bpy.ops.wm.read_factory_settings(use_empty=True)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls._tmpdir, ignore_errors=True)

    def test_exit_without_enter_raises(self):
        ctx = bpy.data.libraries.load(self._libpath, link=True)
        with self.assertRaises(RuntimeError):
            ctx.__exit__(None, None, None)

    def test_double_exit_raises(self):
        ctx = bpy.data.libraries.load(self._libpath, link=True)
        ctx.__enter__()
        ctx.__exit__(None, None, None)
        with self.assertRaises(RuntimeError):
            ctx.__exit__(None, None, None)

    def test_reenter_raises(self):
        ctx = bpy.data.libraries.load(self._libpath, link=True)
        ctx.__enter__()
        with self.assertRaises(RuntimeError):
            ctx.__enter__()
        ctx.__exit__(None, None, None)

    def test_data_from_dummy_exit_raises(self):
        # ``data_from`` is a dummy context object without a blend handle;
        # exiting it must not read uninitialized members.
        ctx = bpy.data.libraries.load(self._libpath, link=True)
        data_from, _data_to = ctx.__enter__()
        with self.assertRaises(RuntimeError):
            data_from.__exit__(None, None, None)
        ctx.__exit__(None, None, None)

    def test_normal_enter_exit_still_works(self):
        with bpy.data.libraries.load(self._libpath, link=True) as (data_from, data_to):
            self.assertIn("Cube", data_from.objects)
            data_to.objects = ["Cube"]
        self.assertEqual(len(bpy.data.objects), 1)
        self.assertEqual(bpy.data.objects[0].name, "Cube")
        bpy.data.objects.remove(bpy.data.objects[0], do_unlink=True)


class TestBLFBindImBufContextManager(unittest.TestCase):
    """``blf.bind_imbuf`` must not pop an uninitialized buffer state on misuse."""

    def setUp(self):
        self.ibuf = imbuf.new((8, 8))
        self.font_id = 0

    def tearDown(self):
        self.ibuf.free()

    def test_exit_without_enter_raises(self):
        ctx = blf.bind_imbuf(self.font_id, self.ibuf, display_name="sRGB")
        with self.assertRaises(ValueError):
            ctx.__exit__(None, None, None)

    def test_double_exit_raises(self):
        ctx = blf.bind_imbuf(self.font_id, self.ibuf, display_name="sRGB")
        ctx.__enter__()
        ctx.__exit__(None, None, None)
        with self.assertRaises(ValueError):
            ctx.__exit__(None, None, None)

    def test_normal_enter_exit_still_works(self):
        with blf.bind_imbuf(self.font_id, self.ibuf, display_name="sRGB"):
            blf.size(self.font_id, 12.0)
            blf.position(self.font_id, 0.0, 0.0, 0.0)


class TestBrushDirectionEnumWithoutContext(unittest.TestCase):
    """Brush ``direction`` enum itemf must not crash when context is unavailable (#161637)."""

    def test_direction_enum_items_accessible(self):
        brush = bpy.data.brushes.new(name="CoverageDirectionBrush")
        try:
            prop = brush.bl_rna.properties["direction"]
            items = list(prop.enum_items)
            self.assertGreaterEqual(len(items), 1)
            # Accessing the value must also succeed in background mode.
            _ = brush.direction
        finally:
            bpy.data.brushes.remove(brush)


def main():
    import sys
    sys.argv = [__file__] + (sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    unittest.main()


if __name__ == "__main__":
    main()
