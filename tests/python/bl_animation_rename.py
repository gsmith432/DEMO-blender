# SPDX-FileCopyrightText: 2026 Blender Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later


import unittest
import bpy
import pathlib
import sys


_BONE_NAME_A = "bone_a"
_BONE_NAME_B = "bone_b"


def _set_up_driver(driver: bpy.types.Driver, target_id: bpy.types.ID, target_path: str) -> None:
    driver_variable_name = "var"

    driver.type = 'AVERAGE'
    driver.expression = driver_variable_name

    driver_var = driver.variables.new()
    driver_var.name = driver_variable_name
    driver_var.type = 'SINGLE_PROP'

    driver_target = driver_var.targets[0]
    driver_target.id_type = target_id.id_type
    driver_target.id = target_id
    driver_target.data_path = target_path


class PoseBoneRenameTest(unittest.TestCase):
    """Ensure that drivers and animation are moved to the correct RNA path once a pose bone is renamed."""

    def setUp(self) -> None:
        super().setUp()
        bpy.ops.wm.read_homefile(use_factory_startup=True)

        armature = bpy.data.armatures.new("test_armature")
        self.armature_obj = bpy.data.objects.new("test_armature_object", armature)
        bpy.context.scene.collection.objects.link(self.armature_obj)
        bpy.context.view_layer.objects.active = self.armature_obj
        self.armature_obj.select_set(True)

        bpy.ops.object.mode_set(mode='EDIT')
        edit_bone = armature.edit_bones.new(_BONE_NAME_A)
        edit_bone.head = (1, 0, 0)
        edit_bone.tail = (0, 0, 0)

        edit_bone = armature.edit_bones.new(_BONE_NAME_B)
        edit_bone.head = (1, 1, 0)
        edit_bone.tail = (0, 1, 0)
        bpy.ops.object.mode_set(mode='OBJECT')

        # This is useful to check if the rename does not affect animation on identically named
        # bones in a different object.
        self.armature_obj_dupli = self.armature_obj.copy()
        self.armature_obj_dupli.data = armature.copy()
        bpy.context.scene.collection.objects.link(self.armature_obj_dupli)

    def test_rename_bone_driver(self) -> None:
        fcu = self.armature_obj.data.bones[_BONE_NAME_A].driver_add("bbone_segments", -1)
        self.assertEqual(fcu.data_path, f'bones["{_BONE_NAME_A}"].bbone_segments')
        _set_up_driver(fcu.driver, self.armature_obj, f'pose.bones["{_BONE_NAME_B}"].location[0]')

        # Setting up the same driver on the duplicate armature.
        fcu_dupli = self.armature_obj_dupli.data.bones[_BONE_NAME_A].driver_add("bbone_segments", -1)
        self.assertEqual(fcu_dupli.data_path, fcu.data_path)
        _set_up_driver(fcu_dupli.driver, self.armature_obj_dupli, f'pose.bones["{_BONE_NAME_B}"].location[0]')

        bone_a_new_name = "bone_a_2"
        self.armature_obj.pose.bones[_BONE_NAME_A].name = bone_a_new_name

        # `bbone_segments` is a property of the bone thus armature.
        self.assertEqual(len(self.armature_obj.data.animation_data.drivers), 1, "Shouldn't remove the driver")
        self.assertEqual(fcu.data_path, f'bones["{bone_a_new_name}"].bbone_segments')

        self.assertEqual(
            fcu_dupli.data_path,
            f'bones["{_BONE_NAME_A}"].bbone_segments',
            "Should not modify duplicate armature")

        bone_b_new_name = "bone_b_2"
        self.armature_obj.pose.bones[_BONE_NAME_B].name = bone_b_new_name

        # Testing if driver targets are still correct after a rename.
        driver_target = fcu.driver.variables[0].targets[0]
        self.assertEqual(driver_target.data_path, f"pose.bones[\"{bone_b_new_name}\"].location[0]")

    def test_rename_pose_bone_driver(self) -> None:
        fcu = self.armature_obj.pose.bones[_BONE_NAME_A].driver_add("hide", -1)
        self.assertEqual(fcu.data_path, f'pose.bones["{_BONE_NAME_A}"].hide')
        _set_up_driver(fcu.driver, self.armature_obj, f'pose.bones["{_BONE_NAME_B}"].location[0]')

        # Setting up the same driver on the duplicate armature.
        fcu_dupli = self.armature_obj_dupli.pose.bones[_BONE_NAME_A].driver_add("hide", -1)
        self.assertEqual(fcu_dupli.data_path, fcu.data_path)
        _set_up_driver(fcu_dupli.driver, self.armature_obj_dupli, f'pose.bones["{_BONE_NAME_B}"].location[0]')

        bone_a_new_name = "bone_a_2"
        self.armature_obj.pose.bones[_BONE_NAME_A].name = bone_a_new_name

        # `hide` is a property on the pose bone thus object.
        self.assertEqual(len(self.armature_obj.animation_data.drivers), 1, "Shouldn't remove the driver")
        self.assertEqual(fcu.data_path, f'pose.bones["{bone_a_new_name}"].hide')

        self.assertEqual(
            fcu_dupli.data_path,
            f'pose.bones["{_BONE_NAME_A}"].hide',
            "Should not modify the duplicate armature")

        bone_b_new_name = "bone_b_2"
        self.armature_obj.pose.bones[_BONE_NAME_B].name = bone_b_new_name

        # Testing if driver targets are still correct after a rename.
        driver_target = fcu.driver.variables[0].targets[0]
        self.assertEqual(driver_target.data_path, f"pose.bones[\"{bone_b_new_name}\"].location[0]")

    def test_rename_bone_animation(self) -> None:
        # Not particularly useful to animate this property, but it can be done, so better test it.
        self.armature_obj.data.bones[_BONE_NAME_A].keyframe_insert("bbone_segments")
        self.assertNotEqual(self.armature_obj.data.animation_data.action, None)
        action = self.armature_obj.data.animation_data.action
        fcurves = action.layers[0].strips[0].channelbags[0].fcurves
        self.assertEqual(fcurves[0].data_path, f'bones[\"{_BONE_NAME_A}"].bbone_segments')

        self.armature_obj_dupli.data.bones[_BONE_NAME_A].keyframe_insert("bbone_segments")
        self.assertNotEqual(self.armature_obj_dupli.data.animation_data.action, None)

        bone_a_new_name = "bone_a_2"
        # Renaming the pose bone also renames the bone itself, which should rename the fcurve data path too.
        self.armature_obj.pose.bones[_BONE_NAME_A].name = bone_a_new_name

        self.assertEqual(fcurves[0].data_path, f'bones[\"{bone_a_new_name}"].bbone_segments')

        dupli_action = self.armature_obj_dupli.data.animation_data.action
        dupli_fcurves = dupli_action.layers[0].strips[0].channelbags[0].fcurves
        self.assertEqual(dupli_fcurves[0].data_path, f'bones[\"{_BONE_NAME_A}"].bbone_segments')

    def test_rename_pose_bone_animation(self) -> None:
        self.armature_obj.pose.bones[_BONE_NAME_A].keyframe_insert("location")
        self.assertNotEqual(self.armature_obj.animation_data.action, None)
        action = self.armature_obj.animation_data.action
        fcurves = action.layers[0].strips[0].channelbags[0].fcurves
        for fcurve in fcurves:
            self.assertEqual(fcurve.data_path, f'pose.bones[\"{_BONE_NAME_A}"].location')

        self.armature_obj_dupli.pose.bones[_BONE_NAME_A].keyframe_insert("location")
        self.assertNotEqual(self.armature_obj_dupli.animation_data.action, None)

        bone_a_new_name = "bone_a_2"
        self.armature_obj.pose.bones[_BONE_NAME_A].name = bone_a_new_name

        for fcurve in fcurves:
            self.assertEqual(fcurve.data_path, f'pose.bones[\"{bone_a_new_name}"].location')

        dupli_action = self.armature_obj_dupli.animation_data.action
        for fcurve in dupli_action.layers[0].strips[0].channelbags[0].fcurves:
            self.assertEqual(fcurve.data_path, f'pose.bones[\"{_BONE_NAME_A}"].location')


class ConstraintRenameDriverCowTest(unittest.TestCase):
    """Constraint rename must refresh evaluated drivers that target the constraint.

    Regression: ``BKE_animdata_fix_paths`` rewrote driver targets on other IDs but only
    tagged the constraint owner. Copy-on-write kept the stale RNA path, so drivers stopped
    resolving until something else refreshed the driven ID.
    """

    def setUp(self) -> None:
        bpy.ops.wm.read_homefile(use_factory_startup=True)
        bpy.ops.object.empty_add()
        self.target_obj = bpy.context.active_object
        self.constraint = self.target_obj.constraints.new('COPY_LOCATION')
        self.constraint.name = "MyCon"
        self.constraint.influence = 0.25

        bpy.ops.object.empty_add(location=(2.0, 0.0, 0.0))
        self.driven_obj = bpy.context.active_object
        fcu = self.driven_obj.driver_add("location", 0)
        fcu.driver.type = 'AVERAGE'
        var = fcu.driver.variables.new()
        var.name = "var"
        var.type = 'SINGLE_PROP'
        tgt = var.targets[0]
        tgt.id = self.target_obj
        tgt.data_path = 'constraints["MyCon"].influence'
        self.driver_target = tgt

        bpy.context.view_layer.update()
        self.assertAlmostEqual(self.driven_obj.location.x, 0.25, places=5)

    def test_constraint_rename_keeps_evaluated_driver_working(self) -> None:
        self.constraint.name = "MyConRenamed"
        bpy.context.view_layer.update()

        self.assertEqual(self.driver_target.data_path, 'constraints["MyConRenamed"].influence')

        depsgraph = bpy.context.evaluated_depsgraph_get()
        driven_eval = self.driven_obj.evaluated_get(depsgraph)
        eval_path = driven_eval.animation_data.drivers[0].driver.variables[0].targets[0].data_path
        self.assertEqual(
            eval_path,
            'constraints["MyConRenamed"].influence',
            "Evaluated driver target must sync after constraint rename",
        )

        self.constraint.influence = 0.75
        bpy.context.view_layer.update()
        self.assertAlmostEqual(
            self.driven_obj.location.x,
            0.75,
            places=5,
            msg="Driver must keep resolving after constraint rename",
        )


if __name__ == "__main__":
    import sys
    sys.argv = [__file__] + (sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    unittest.main()
