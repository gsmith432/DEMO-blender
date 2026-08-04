/* SPDX-FileCopyrightText: 2026 Blender Authors
 *
 * SPDX-License-Identifier: GPL-2.0-or-later */

#include "testing/testing.h"

#include "BLI_listbase.hh"

#include "BKE_gtest_base.hh"
#include "BKE_idtype.hh"
#include "BKE_key.hh"
#include "BKE_lib_id.hh"
#include "BKE_main.hh"
#include "BKE_mesh.hh"

#include "BLO_blend_validate.hh"

#include "DNA_key_types.h"
#include "DNA_mesh_types.h"

namespace blender {

class BlendValidateTest : public bke::BlenderGTestBase {};

/**
 * Regression for #161868: deleting an orphaned shape key during validation must use
 * `prevent_invariants_update` because Main may not be fully constructed (e.g. readfile).
 * This exercises the delete path that previously crashed via `BKE_main_ensure_invariants`.
 */
TEST_F(BlendValidateTest, ShapekeysDeleteOrphanedWithoutInvariantsUpdate)
{
  Main *bmain = BKE_main_new();

  Mesh *mesh = BKE_mesh_add(bmain, "Mesh");
  Key *valid_key = BKE_key_add(bmain, &mesh->id);
  mesh->key = valid_key;
  ASSERT_EQ(valid_key->from, &mesh->id);

  Key *orphan_key = BKE_key_add(bmain, &mesh->id);
  ASSERT_NE(orphan_key, nullptr);
  /* Simulate corrupt/orphaned shape key as found during blendfile validation. */
  orphan_key->from = nullptr;

  EXPECT_EQ(BLI_listbase_count(&bmain->shapekeys), 2);

  const bool is_valid = BLO_main_validate_shapekeys(bmain, nullptr);
  /* Orphan deletion does not flip the return value; only broken `from` remaps do. */
  EXPECT_TRUE(is_valid);

  EXPECT_EQ(BLI_listbase_count(&bmain->shapekeys), 1);
  EXPECT_EQ(bmain->shapekeys.first, valid_key);
  EXPECT_EQ(valid_key->from, &mesh->id);
  EXPECT_EQ(mesh->key, valid_key);

  BKE_main_free(bmain);
}

TEST_F(BlendValidateTest, ShapekeysRepairInvalidFromPointer)
{
  Main *bmain = BKE_main_new();

  Mesh *mesh_a = BKE_mesh_add(bmain, "MeshA");
  Mesh *mesh_b = BKE_mesh_add(bmain, "MeshB");
  Key *key = BKE_key_add(bmain, &mesh_a->id);
  mesh_a->key = key;
  /* Point at the wrong owner ID (still non-null, so it is not deleted). */
  key->from = &mesh_b->id;

  const bool is_valid = BLO_main_validate_shapekeys(bmain, nullptr);
  EXPECT_FALSE(is_valid);
  EXPECT_EQ(key->from, &mesh_a->id);
  EXPECT_EQ(BLI_listbase_count(&bmain->shapekeys), 1);

  BKE_main_free(bmain);
}

TEST_F(BlendValidateTest, IdDeletePreventInvariantsUpdateStillRemovesID)
{
  Main *bmain = BKE_main_new();
  Mesh *mesh = BKE_mesh_add(bmain, "Mesh");
  Key *key = BKE_key_add(bmain, &mesh->id);
  mesh->key = nullptr;
  key->from = nullptr;

  BKE_id_delete(bmain, &key->id, {.prevent_invariants_update = true});

  EXPECT_EQ(BLI_listbase_count(&bmain->shapekeys), 0);
  EXPECT_EQ(BLI_listbase_count(&bmain->meshes), 1);

  BKE_main_free(bmain);
}

}  // namespace blender
