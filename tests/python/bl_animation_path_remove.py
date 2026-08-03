# SPDX-FileCopyrightText: 2026 Blender Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""
Tests for BKE_animdata_fix_paths_remove / animation cleanup on ID path removal.

blender -b --factory-startup --python tests/python/bl_animation_path_remove.py
"""

import unittest

import bpy


def _fcurves_of(action: bpy.types.Action) -> list[tuple[str, int]]:
    out: list[tuple[str, int]] = []
    for layer in action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                out.extend((fcurve.data_path, fcurve.array_index) for fcurve in bag.fcurves)
    return out


class AnimDataPathRemoveTweakStorageTest(unittest.TestCase):
    """Deleting animated RNA must also clear FCurves on NLA tweak-storage Actions."""

    def setUp(self) -> None:
        bpy.ops.wm.read_factory_settings(use_empty=True)

        self.node_group = bpy.data.node_groups.new("PathRemoveSG", "ShaderNodeTree")
        self.node = self.node_group.nodes.new("ShaderNodeValue")
        self.node.name = "AnimatedValue"
        self.node_group.animation_data_create()

    def _keyed_action(self, name: str, value: float) -> bpy.types.Action:
        action = bpy.data.actions.new(name)
        self.node_group.animation_data.action = action
        self.node.outputs[0].default_value = value
        self.assertTrue(self.node.outputs[0].keyframe_insert("default_value", frame=1))
        self.assertTrue(action.slots)
        self.node_group.animation_data.action_slot = action.slots[0]
        self.assertEqual(
            _fcurves_of(action),
            [('nodes["AnimatedValue"].outputs[0].default_value', 0)],
        )
        return action

    def test_remove_paths_clears_action_tweak_storage(self) -> None:
        """
        While NLA tweak-mode is active, AnimData.action is the strip Action and
        action_tweak_storage holds the previously assigned Action. Removing a node
        must delete matching FCurves from both.
        """
        action_strip = self._keyed_action("StripAct", 0.25)
        action_stashed = self._keyed_action("StashedAct", 0.5)

        adt = self.node_group.animation_data
        adt.action = action_strip
        adt.action_slot = action_strip.slots[0]
        adt.action_tweak_storage = action_stashed
        # Mirror real tweak-mode: the stashed Action keeps its own slot handle.
        adt.action_slot_handle_tweak_storage = action_stashed.slots[0].handle

        self.assertEqual(adt.action, action_strip)
        self.assertEqual(adt.action_tweak_storage, action_stashed)

        self.node_group.nodes.remove(self.node)

        self.assertEqual(_fcurves_of(action_strip), [], "Strip Action FCurves should be removed")
        self.assertEqual(
            _fcurves_of(action_stashed),
            [],
            "Tweak-storage Action FCurves must be removed too (not left as orphans, "
            "and not deleted from the wrong Action/slot)",
        )


if __name__ == "__main__":
    import sys

    sys.argv = [__file__] + (sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    unittest.main()
