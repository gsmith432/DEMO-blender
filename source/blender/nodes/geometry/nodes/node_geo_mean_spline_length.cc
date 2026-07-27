/* SPDX-FileCopyrightText: 2026 Blender Authors
 *
 * SPDX-License-Identifier: GPL-2.0-or-later */

#include "BKE_curves.hh"
#include "BKE_grease_pencil.hh"

#include "node_geometry_util.hh"

namespace blender::nodes::node_geo_mean_spline_length_cc {

static void node_declare(NodeDeclarationBuilder &b)
{
  b.add_input<decl::Geometry>("Curve"_ustr)
      .supported_type({GeometryComponent::Type::Curve, GeometryComponent::Type::GreasePencil})
      .description("Curve to compute the mean spline length of");
  b.add_output<decl::Float>("Length"_ustr);
}

static void accumulate_curves_length(const bke::CurvesGeometry &curves,
                                     float &r_total_length,
                                     int &r_spline_count)
{
  const VArray<bool> cyclic = curves.cyclic();
  curves.ensure_evaluated_lengths();

  for (const int i : curves.curves_range()) {
    r_total_length += curves.evaluated_length_total_for_curve(i, cyclic[i]);
  }
  r_spline_count += curves.curves_num();
}

static void node_geo_exec(GeoNodeExecParams params)
{
  GeometrySet geometry_set = params.extract_input<GeometrySet>("Curve"_ustr);
  float total_length = 0.0f;
  int spline_count = 0;
  if (geometry_set.has_curves()) {
    const Curves &curves_id = *geometry_set.get_curves();
    const bke::CurvesGeometry &curves = curves_id.geometry.wrap();
    accumulate_curves_length(curves, total_length, spline_count);
  }
  else if (geometry_set.has_grease_pencil()) {
    using namespace bke::greasepencil;
    const GreasePencil &grease_pencil = *geometry_set.get_grease_pencil();
    for (const int layer_index : grease_pencil.layers().index_range()) {
      const Drawing *drawing = grease_pencil.get_eval_drawing(grease_pencil.layer(layer_index));
      if (drawing == nullptr) {
        continue;
      }
      const bke::CurvesGeometry &curves = drawing->strokes();
      accumulate_curves_length(curves, total_length, spline_count);
    }
  }
  else {
    params.set_default_remaining_outputs();
    return;
  }

  const float mean_length = (spline_count > 0) ? (total_length / float(spline_count)) : 0.0f;
  params.set_output("Length"_ustr, mean_length);
}

static void node_register()
{
  static bke::bNodeType ntype;

  geo_node_type_base(&ntype, "GeometryNodeMeanSplineLength"_ustr);
  ntype.ui_name = "Mean Spline Length";
  ntype.ui_description = "Retrieve the average length of all splines";
  ntype.nclass = NODE_CLASS_GEOMETRY;
  ntype.declare = node_declare;
  ntype.geometry_node_execute = node_geo_exec;
  bke::node_register_type(ntype);
}
NOD_REGISTER_NODE(node_register)

}  // namespace blender::nodes::node_geo_mean_spline_length_cc
