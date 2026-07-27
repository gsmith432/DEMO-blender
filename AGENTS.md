# AGENTS.md

## Cursor Cloud specific instructions

This repository is **Blender** — a C/C++ 3D creation suite with an embedded Python
API. It is a single CMake project (no web/backend services, no database). Official
build docs: https://developer.blender.org/docs/handbook/building_blender/linux/

### Build directory must be outside `/workspace`
Blender enforces an out-of-source build and the `GNUmakefile` defaults `BUILD_DIR`
to the repo's *parent* directory. Here the repo is `/workspace`, whose parent `/`
is **not writable**. Always pass an explicit writable `BUILD_DIR`, e.g.
`/home/ubuntu/build_linux_lite`. This is the durable dev build location.

### Building (dev mode)
```
make lite ninja ccache BUILD_DIR=/home/ubuntu/build_linux_lite
```
`lite` is the fast dev build (minimal features; no Cycles/OpenSubdiv/audio) and is
what has been verified here. Other profiles: `make developer` (adds `WITH_GTESTS`,
ASAN, `compile_commands.json`), `make full`, `make headless`, `make bpy`. Non-lite
profiles compile far more and take much longer. First full compile of `lite` is
~20-25 min on this 4-core VM; `ccache` makes rebuilds much faster.

Gotcha: the install step writes runtime scripts/datafiles next to the binary. The
portable install prefix (`${BUILD_DIR}/bin`) is only auto-set on the **first**
successful CMake configure (`CMAKE_INSTALL_PREFIX_INITIALIZED_TO_DEFAULT`). If an
earlier configure failed and left `/usr/local` cached, install fails with
`cannot make directory "/usr/local/5.3/scripts"`. Fix by reconfiguring with
`cmake -DCMAKE_INSTALL_PREFIX=/home/ubuntu/build_linux_lite/bin . && ninja install`
from the build dir (compile is cached). A clean first build avoids this.

### Running (headless / scripting)
```
/home/ubuntu/build_linux_lite/bin/blender --version
/home/ubuntu/build_linux_lite/bin/blender --background --factory-startup --python <script.py>
```
GUI needs a display server + working OpenGL/Vulkan; headless `--background` scripting
via the `bpy` API is the reliable path in this VM.

### Lint
Blender bundles clang-format at `lib/linux_x64/llvm/bin/clang-format` (fetched by
`make update`). `make format PATHS="…"` reformats in place (C/C++ via clang-format,
Python via autopep8). For a non-modifying check use
`lib/linux_x64/llvm/bin/clang-format --dry-run --Werror <file>`. Other checks:
`make check_pep8`, `make check_mypy`, `make check_cmake`, `make check_licenses`.

### Tests
CTest + GoogleTest require a build with `WITH_GTESTS` (i.e. `make developer …`),
then `ctest --output-on-failure` from the build dir (or `make test`). Python
integration tests under `tests/python/` run the built binary in `--background`
against assets in `tests/files/`. These were not built here (the `lite` profile
omits gtests); build with `developer` if tests are needed.

### System dependencies (already present in the VM snapshot)
Installed via the repo script `python3 build_files/linux/install_linux_packages.py`
(compilers, X11/Wayland/GL dev libs, ninja) plus `ccache`. **Critical extra:** the
default `/usr/bin/c++` is `clang++`, which uses the gcc-14 toolchain, so
`libstdc++-14-dev` must be installed (the Blender installer does not add it). Without
it, configure fails with `cannot find -lstdc++`.

### Precompiled libraries
`make update` (run by the startup update script as `make_update.py --no-blender`)
fetches the pinned `lib/linux_x64` submodule (~2.3 GB via Git LFS) from
projects.blender.org. It is idempotent and a fast no-op when already current.

### Expected `git status` noise (Git LFS)
After Git LFS is initialized, `git status` reports thousands of tracked binary
assets (under `assets/`, `release/`, `doc/`, etc.) as "modified" due to LFS
smudge/pointer differences. This is pre-existing and unrelated to your work — do
**not** `git add -A` / commit these. Stage only the specific files you changed.

### Demo node
`source/blender/nodes/geometry/nodes/node_geo_demo_review.cc` contains intentional
convention violations for the geometry-node review automation and is deliberately
**not** registered in any `CMakeLists.txt` `SRC` list (it references an undefined
`GEO_NODE_DEMO_REVIEW`), so it is not compiled and does not affect the build.
