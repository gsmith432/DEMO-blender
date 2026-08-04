# SPDX-FileCopyrightText: 2026 Blender Authors
#
# SPDX-License-Identifier: Apache-2.0

"""
Regression for #161772: accessing RNA Function parameters must not assert.

After ca2cefe975, Function was briefly marked STRUCT_RNA_DEFINITION. Console
autocomplete (and any RNA introspection of function parameters) then hit
`rna_property_can_access_pointer_data` asserts because Function parameters are
not tagged as meta-definition properties. Function is intentionally not a
meta-type so parameter properties remain accessible.
"""

import bpy
import unittest


class TestRnaFunctionParameters(unittest.TestCase):
    def test_object_function_parameters_accessible(self):
        fn = bpy.types.Object.bl_rna.functions.get("select_set")
        self.assertIsNotNone(fn)
        self.assertEqual(fn.identifier, "select_set")

        params = list(fn.parameters)
        self.assertGreaterEqual(len(params), 1)

        state = next(p for p in params if p.identifier == "state")
        self.assertEqual(state.type, 'BOOLEAN')
        # Touch attributes used by console/API introspection paths.
        _ = state.description
        _ = state.is_required
        _ = state.is_output
        _ = state.is_runtime

    def test_function_parameters_across_types(self):
        """Walk a sample of RNA functions; any assert here is a regression."""
        checked = 0
        sample_types = (
            bpy.types.Object,
            bpy.types.Mesh,
            bpy.types.Scene,
            bpy.types.Material,
            bpy.types.NodeTree,
            bpy.types.WindowManager,
        )
        for rna_type in sample_types:
            for fn in rna_type.bl_rna.functions:
                checked += 1
                self.assertTrue(fn.identifier)
                for param in fn.parameters:
                    self.assertTrue(param.identifier)
                    _ = param.type
                    _ = param.is_required
                    _ = param.is_output
                    _ = param.is_runtime
                    if param.type == 'ENUM' and hasattr(param, "enum_items"):
                        _ = len(param.enum_items)
                    if getattr(param, "is_array", False):
                        _ = param.array_length

        self.assertGreater(checked, 20)


if __name__ == "__main__":
    import sys
    sys.argv = [__file__] + (sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    unittest.main()
