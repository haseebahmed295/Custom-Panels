# `my_engine` C++ Native Module Build

This directory contains the C++ source and build setup for the `my_engine` native extension module.

## Files

- **`my_engine.cpp`**: C++ source implementing pybind11 module bindings and safe memory reading routines against Blender's DNA memory structures.
- **`setup.py`**: Python `setuptools` build configuration targeting C++17.
- **`blender-main/`**: Subtree containing required Blender DNA header files (`source/blender/makesdna`, `intern/guardedalloc`, `source/blender/blenlib`).

## Prerequisites

- **Python 3.13** (matching Blender's embedded Python runtime).
- **Microsoft Visual C++ Build Tools** (MSVC 2019/2022 supporting C++17).
- **pybind11**: `pip install pybind11`

## Building

To compile the C++ extension in-place:

```powershell
python setup.py build_ext --inplace
```

This will produce a `.pyd` file (e.g. `my_engine.cp313-win_amd64.pyd`). Copy this binary into the parent directory so Blender's Python runtime can import it.

For detailed API and architectural documentation, refer to [**`docs/my_engine.md`**](../docs/my_engine.md).
