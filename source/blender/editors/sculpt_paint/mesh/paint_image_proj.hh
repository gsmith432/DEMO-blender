/* SPDX-FileCopyrightText: 2026 Blender Authors
 *
 * SPDX-License-Identifier: GPL-2.0-or-later */

/** \file
 * \ingroup edsculpt
 *
 * Shared helpers for projected image painting (Texture Paint).
 */

#pragma once

#include "BLI_math_geom_c.hh"

namespace blender::ed::sculpt_paint {

/**
 * UV triangle area used by Texture Paint seam-bleed degeneracy checks.
 *
 * Single-value UV maps collapse to a point in UV space, so they are treated as
 * degenerate (area 0). For normal UV spans, returns the positive 2D triangle area.
 *
 * A regression that discarded #area_tri_v2's return and hard-coded 0 marked every
 * face degenerate whenever seam bleed was enabled, silently disabling bleed.
 */
inline float project_paint_bleed_uv_tri_area(const bool has_single_value_uv,
                                             const float uv0[2],
                                             const float uv1[2],
                                             const float uv2[2])
{
  if (has_single_value_uv) {
    return 0.0f;
  }
  return area_tri_v2(uv0, uv1, uv2);
}

}  // namespace blender::ed::sculpt_paint
