# Custom GPU UI Engine (`my_engine`)

A Blender extension and native C++ memory bridge for rendering pixel-perfect custom GPU overlays inside Blender's N-Panel (Sidebar).

## Overview

Blender's Python API does not natively expose runtime pixel dimensions, scroll positions, or category tab selections for sidebar panels. **`my_engine`** solves this by providing an in-process C++ pybind11 extension that inspects Blender's DNA structures (`ARegion`, `Panel`, `View2D`, `PanelCategoryStack`) safely via Windows `ReadProcessMemory`.

## Documentation

- 📘 [**`my_engine` Library Documentation**](docs/my_engine.md): Complete architecture, API reference, coordinate transformation math, build steps, and troubleshooting.
- 📝 [**Experience Report**](docs/experience_report.md): Technical lessons learned, coordinate systems, GPU rendering bottlenecks, and API changes.

## Quickstart

### 1. Build the Native Library (Optional if `.pyd` is already present)

```powershell
cd Cpp_compile
python setup.py build_ext --inplace
```

Move or copy the generated `my_engine.*.pyd` into the repository root.

### 2. Install / Run in Blender

1. Link or copy this directory into your Blender scripts/addons folder, or open Blender and run `__init__.py`.
2. In the 3D Viewport, press `N` to open the sidebar.
3. Switch to the **My Engine** tab.
4. The addon will automatically detect tab focus, calculate panel boundaries via `my_engine`, and render the GPU canvas overlay.

## Repository Structure

```
├── Cpp_compile/
│   ├── my_engine.cpp       # C++ pybind11 native memory inspection source
│   ├── setup.py            # setuptools build configuration
│   └── blender-main/       # Blender DNA source header dependencies
├── docs/
│   ├── my_engine.md        # Technical API and architecture documentation
│   └── experience_report.md# Experience report on GPU UI overlays
├── bl_ui_widgets/          # UI widget components (buttons, sliders, textboxes)
├── __init__.py             # Add-on entry point and N-Panel registration
├── gpu_core.py             # GPU drawing manager and lifecycle watchdog timer
├── event_handler.py        # Modal operator for mouse/keyboard interactions
├── ui_elements.py          # 2D batch shader geometry and UI element tree
├── sample.py               # Standalone reference implementation
└── my_engine.cp313-win_amd64.pyd # Precompiled Windows x64 binary (Python 3.13)
```
