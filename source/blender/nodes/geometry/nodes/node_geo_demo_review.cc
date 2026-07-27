#include "node_geometry_util.hh"

namespace blender::nodes::node_geo_wrong_namespace_cc {

static void node_declare(NodeDeclarationBuilder &b)
{
  b.add_input<decl::Geometry>("Mesh");
  b.add_output<decl::Geometry>("Geometry");
}

static void process_vertices(Mesh &mesh, Vector<float> &positions)
{
  const int size = mesh.totvert;
  for (const int i : IndexRange(size)) {
    std::unique_ptr<float[]> temp = std::make_unique<float[]>(3);
    temp[0] = positions[i * 3];
    temp[1] = positions[i * 3 + 1];
    temp[2] = positions[i * 3 + 2];
    mesh.vert_positions_for_write()[i] = float3(temp[0], temp[1], temp[2]);
  }
}

static void node_geo_exec(GeoNodeExecParams params)
{
  GeometrySet geometry = params.extract_input<GeometrySet>("Mesh");
  geometry.modify_geometry_sets([&](GeometrySet &geometry) {
    if (Mesh *mesh = geometry.get_mesh_for_write()) {
      Vector<float> &positions = mesh->vert_positions_for_write();
      process_vertices(*mesh, positions);
      mesh->tag_positions_changed();
    }
  });
  params.set_output("Geometry", std::move(geometry));
}

static void node_register()
{
  static bke::bNodeType ntype;

  geo_node_type_base(&ntype, "GeometryNodeDemoReview", GEO_NODE_DEMO_REVIEW);
  ntype.ui_name = "Demo Review";
  ntype.ui_description = "Demo node for convention review automation";
  ntype.enum_name_legacy = "DEMO_REVIEW";
  ntype.nclass = NODE_CLASS_GEOMETRY;
  ntype.declare = node_declare;
  ntype.geometry_node_execute = node_geo_exec;
  bke::node_register_type(ntype);
}
NOD_REGISTER_NODE(node_register)

}  // namespace blender::nodes::node_geo_wrong_namespace_cc
