# SVR Visual Compatibility Generator 0.4.1 Beta

Source for an optional Skyrim VR mesh compatibility tool. It copies render geometry,
UVs and shader/material references from locally installed graphics meshes into supported
SVR Physical Doors / Containers meshes, preserving their Havok blocks byte for byte.

## Changes in 0.4.1
- Converts supported Skyrim LE (BS 83) donor meshes to SE format before transferring geometry and materials.
- Records skipped models with their path, processing stage, and error in the manifest and continues with the other models.
- Verified with the reported Riften door sample and a 209-model comparison against 0.4. In-game PBR rendering on the reported setup is pending confirmation.

## Source map
- `gui/Wizard.cs`: Windows Forms launcher (English/Russian), folder selection, mod detection.
- `app/gui_worker.py`: input validation, generation workflow, output ZIP and summary.
- `app/generate.py`: model mappings, native-helper invocation, render/physics validation.
- `app/barrel_cap.py`, `app/split_barrel.py`: solid cap selection/splitting.
- `app/nif_io.py`: lossless NIF block reader/writer; `app/profiles.json`: supported mappings.
- `native/graft.cpp`: native render geometry/material grafting; bundled nifly dependency.
- `legacy-0.3/`: source snapshot extracted from the quarantined 0.3 release ZIP.
- `RELEASE-HASHES.json`: exact published/prepared archive and executable SHA256 values.

No Skyrim, SMIM, Vanilla PBR or Vanaheimr meshes/textures are included in this repository.

## Build prerequisites
Windows x64; Visual Studio Build Tools with MSVC C++17 and Windows SDK; CMake 3.20+
(use a version supporting your installed Visual Studio); .NET Framework compiler.

Download the official CPython 3.14.10 Windows embeddable x64 ZIP:
https://www.python.org/ftp/python/3.14.10/python-3.14.10-embed-amd64.zip
SHA256: 90905e64a840557d8c1bc4f5b74db3d7ee85e3ffb217611cac1c7813acea4159
The build verifies this hash. The runtime is copied locally, not installed in Windows.
Its license is Python-LICENSE.txt. Runtime sources: https://www.python.org/downloads/source/

Open an x64 Developer PowerShell for Visual Studio, then change to this repository.
Ensure the Windows SDK tools (rc.exe, mt.exe), MSVC and CMake/Ninja are available on PATH.
From that developer shell:

    .uild.ps1 -PythonZip "C:\Downloads\python-3.14.10-embed-amd64.zip"

If CMake is not on PATH, pass `-CMakeExe "C:\path	o\cmake.exe"`.
Optionally pass `-Generator "Visual Studio 17 2022"` (or your installed generator).
Output: `build/SVR Visual Compatibility Generator/`.
The script builds the C++ helper and C# launcher and copies the Python application sources
and official embedded interpreter. It does not download files or change game/mod folders.
Cross-compiler bit-for-bit executable reproducibility is not claimed.

## Runtime behavior for security review
The launcher starts only the bundled `runtime/python.exe` and native `app/SVRVisualPatch.exe`.
The Open result button launches Windows Explorer for the generated ZIP.
Inputs are user-selected local directories. Their files are read, never replaced.
Outputs go to a new, separate user-selected folder; existing output folders are rejected.
The tool does not perform network requests, install services, schedule tasks, modify the
registry, inject into Skyrim, modify MO2 profiles, or disable security settings.
The release is unsigned and contains executable files. The embedded Python standard
library is a ZIP (`python314.zip`); this is part of Python's official embedded package.
This is a description of intended code behavior, not an independent malware certification.

## Licenses
Generator: GPL-3.0-or-later (COPYING.txt). nifly: nifly-LICENSE.txt.
Python: Python-LICENSE.txt. Third-party graphics assets are supplied by each user's
installation; generated output remains subject to those assets' original permissions.
