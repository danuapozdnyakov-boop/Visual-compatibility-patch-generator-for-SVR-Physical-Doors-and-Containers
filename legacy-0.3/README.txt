SVR Physical Doors / Containers — Visual Compatibility Generator 0.3 (Beta)

Generates an optional mesh overlay from your installed visual replacers. No textures,
ESP, SKSE DLL or original game assets are distributed with this generator.

Requirements: Windows x64, Python 3.10+, the base SVR mod(s), and the visual mods you use.
For True PBR, install its rendering requirements and generate donor meshes with PGPatcher
AFTER SMIM, Vanilla PBR and Vanaheimr (enable processing of all meshes).
The donor directory must contain the final original-path meshes, e.g. meshes/clutter/barrel01.nif.
Keep the SVR mod folders and original graphics output as separate inputs.

Run from this directory (replace the paths):
python generate.py --donor-meshes "D:/PGPatcher Output/meshes" --doors "D:/MO2/mods/SVRPhysicalDoors" --containers "D:/MO2/mods/SVRPhysicalContainers" --output "D:/SVR Visual Patch"

Install the resulting output folder as a mod AFTER the base SVR mods and graphics output.
This overlay must win conflicts for the private svrphysicaldoors*/svrphysicalcontainers* paths.
Do not install it in a non-PBR profile if the donor meshes use PBR materials.
Rerun after updating SVR meshes or visual replacers. Disable old visual overlays before generating.
Check reports/manifest.json: unsupported models are not modified; never ignore errors.
Use a fresh output directory for each run. The generator refuses a nonempty output mesh directory.

Validated structurally against SMIM 2.08, Vanilla PBR 1.33.1, Vanaheimr Farmhouses II 3.0
using PGPatcher 2.3.1. Public baseline: Doors 0.1.35 / Containers 0.2.8.
Local baseline: Doors 0.1.40 / Containers 0.2.10. These inputs are not interchangeable.
The tool reads the base meshes, preserving their Havok blocks byte for byte, and replaces
render geometry with the donor's shapes, UVs, shaders and texture bindings. Original physics
bounds remain unchanged; SMIM geometry may differ slightly from the original collision.
SMIM furniture aliases and splitting the three supported barrel lid models are included.
The special Sky Haven Temple head door receives materials only, retaining its existing geometry.
Arbitrary replacers with renamed or merged moving parts are not guaranteed supported.
Custom dark interior fills are retained. Textures must remain installed separately.
No headset or visual rendering verification has been performed for this generated patch.

Physics does not require PBR or this generator. Use it only with your chosen graphics mods.

Source: source/graft.cpp, nifly/; build with CMake and an x64 C++17 compiler.
License: GPL-3.0-or-later; nifly's bundled license applies to its source.
The generated local overlay contains assets from your donor mods. Their original permissions
still apply to redistribution; the generator's code license does not relicense those assets.

0.2: Fixed unlinking of original render surfaces. Reachability checks reject duplicated old surfaces and mismatched donor surface counts.

0.3: Use an existing solid barrel cap where available; reject annular hoop geometry. Rebuild overlays after changing a mesh replacer.
