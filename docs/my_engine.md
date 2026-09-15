# `my_engine` Library Documentation

`my_engine` is a native C++ extension library built with [pybind11](https://github.com/pybind/pybind11) for Blender. It serves as a zero-overhead, crash-safe memory bridge that allows Python scripts and add-ons to query Blender's internal runtime DNA structures (`ARegion`, `Panel`, `View2D`, `PanelCategoryStack`) in-process.

---

## Table of Contents

1. [Motivation & Purpose](#motivation--purpose)
2. [Key Features](#key-features)
3. [Architecture & Safety Design](#architecture--safety-design)
4. [Blender DNA Data Structures](#blender-dna-data-structures)
5. [API Reference](#api-reference)
   - [`get_region_panels`](#1-get_region_panels)
   - [`get_active_category`](#2-get_active_category)
   - [`get_region_scroll`](#3-get_region_scroll)
6. [Coordinate Space & Transformation Math](#coordinate-space--transformation-math)
7. [Build & Compilation Guide](#build--compilation-guide)
8. [Integration Guide & Example Usage](#integration-guide--example-usage)
9. [Cross-Platform Portability](#cross-platform-portability)
10. [Troubleshooting & FAQs](#troubleshooting--faqs)

---

## Motivation & Purpose

### The Blender Python Limitation

Blender provides a comprehensive Python API (`bpy`) for registering panels (`bpy.types.Panel`) inside the 3D View Sidebar (the N-Panel, region type `'UI'`). However, the Python API does **not** expose runtime layout metrics:

- The exact pixel position `(x, y)` of a panel on screen.
- The width and height `(w, h)` of a rendered panel.
- Whether a panel is currently expanded or collapsed (`is_open`).
- The current vertical scroll offset within the sidebar's `View2D` canvas.
- The currently active N-panel tab / category (`PanelCategoryStack`).

When developing custom GPU overlays (e.g. rendering interactive widgets, 3D model previews, or custom viewports with `gpu` and `gpu_extras`), Python developers cannot reliably place graphics inside a panel or know when their tab is visible.

### The Solution: `my_engine`

`my_engine` bridges this gap by directly inspecting Blender's C/C++ memory structures using the memory address of the region (`region.as_pointer()`). It retrieves real-time panel geometries, category tab status, and scroll coordinates in sub-millisecond execution times without modifying Blender's source code or requiring custom Blender builds.

```
+-------------------------------------------------------------+
|                     Blender Runtime                         |
|                                                             |
|   +-------------------+          +----------------------+   |
|   |  ARegion (DNA)    |  memory  |   my_engine (C++)    |   |
|   |  - panels list    |<---------|   - safe_mem_read()  |   |
|   |  - v2d scroll     | address  |   - pybind11 module  |   |
|   |  - active category|          +----------------------+   |
|   +-------------------+                      |              |
|                                              | Python API   |
|                                              v              |
|   +-----------------------------------------------------+   |
|   |   Python Addon (gpu_core.py / ui_elements.py)       |   |
|   |   - Precise GPU overlays matching panel bounds      |   |
|   +-----------------------------------------------------+   |
+-------------------------------------------------------------+
```

---

## Key Features

- **Crash-Safe Memory Reading**: Uses Windows `ReadProcessMemory` to prevent access violations and segfaults when inspecting dynamic or transient Blender pointers.
- **Recursive Hierarchy Traversal**: Automatically navigates nested sub-panels up to 500 nodes with cyclic corruption protection.
- **Real-Time Scroll Tracking**: Computes true visible coordinates by extracting `v2d.cur` view bounds.
- **Zero Runtime Dependencies**: Links directly against Blender's DNA headers (`makesdna`) without needing Blender link libraries or DLL injection.
- **High Performance**: Native C++ execution with minimal memory allocations; suitable for 60 FPS viewport draw callbacks and watchdog timers.

---

## Architecture & Safety Design

### Crash-Safe Memory Access (`safe_mem_read`)

Directly dereferencing raw pointers (`*ptr`) passed from Python can cause fatal Access Violations (Exception `0xC0000005`) if:
- A panel is destroyed between Python calls.
- A pointer points to unmapped or paged-out memory.
- Pointer alignment or struct layouts change.

To guarantee host stability, `my_engine` implements `safe_mem_read`:

```cpp
bool safe_mem_read(const void* target_address, void* local_buffer, size_t size) {
    if (target_address == nullptr) return false;
    SIZE_T bytes_read = 0;
    return (ReadProcessMemory(GetCurrentProcess(), target_address, local_buffer, size, &bytes_read) 
            && bytes_read == size);
}
```

By querying the OS kernel through `ReadProcessMemory` on `GetCurrentProcess()`, invalid memory addresses return `false` gracefully rather than triggering a process-level crash.

---

## Blender DNA Data Structures

`my_engine` inspects four primary DNA structures defined in Blender's source tree:

### 1. `ARegion` (`DNA_screen_types.h`)
Represents an area subdivision (e.g. the `'UI'` sidebar region).
- `panels` (`ListBase`): Linked list of all panels belonging to this region.
- `panels_category_active` (`ListBase`): Stack of active category tabs.
- `v2d` (`View2D`): 2D view transformation and scrolling configuration.

### 2. `Panel` (`DNA_screen_types.h`)
Represents a single UI panel inside the region.
- `panelname` (`char[64]`): The unique identifier (matches `bl_idname`).
- `drawname` (`char*`): Pointer to the display title string (matches `bl_label`).
- `ofsx`, `ofsy` (`int`): Relative pixel coordinates from the parent or canvas top.
- `sizex`, `sizey` (`int`): Dimensions of the panel in pixels.
- `flag` (`int`): Bitmask containing panel state. Bit `(1 << 2)` (`0x04`) indicates `PNL_CLOSED`. If set, the panel is collapsed; if clear, the panel is open.
- `children` (`ListBase`): Linked list of sub-panels nested within this panel.
- `next` (`Panel*`): Pointer to the next sibling panel.

### 3. `PanelCategoryStack` (`DNA_screen_types.h`)
- `idname` (`char[64]`): Name of the category tab currently selected (e.g., `"My Engine"`, `"Item"`, `"Tool"`).

### 4. `View2D` & `rctf` (`DNA_view2d_types.h`, `DNA_vec_types.h`)
- `cur` (`rctf`): The visible bounding rectangle of the virtual 2D canvas:
  - `cur.xmin`, `cur.xmax`: Horizontal canvas limits.
  - `cur.ymin`, `cur.ymax`: Vertical canvas limits. `cur.ymax` tracks the vertical scroll offset from the canvas top.

---

## API Reference

The compiled module `my_engine` exposes three functions:

### 1. `get_region_panels`

Recursively traverses and returns geometry and status for all panels in the specified region.

```python
my_engine.get_region_panels(region_ptr: int, target_name: str = "") -> list[dict]
```

#### Parameters:
- **`region_ptr`** (`int`): The native memory address of the Blender region. Obtain via `bpy.types.Region.as_pointer()`. If `0`, an empty list is returned.
- **`target_name`** (`str`, optional): Filter string. Defaults to `""`.
  - If `""`: Returns all panels and sub-panels in the region.
  - If specified: Returns only panels whose `idname` or `label` matches `target_name`.

#### Return Value:
Returns a `list` of dictionaries. Each dictionary contains:

| Key | Type | Description |
|---|---|---|
| `idname` | `str` | Internal panel identifier name (e.g., `"CUSTOM_PT_gpu_canvas"`). |
| `label` | `str` | Display title of the panel (e.g., `"Custom GPU Engine"`). Returns `""` if untitled. |
| `is_open` | `bool` | `True` if panel is expanded, `False` if collapsed. Evaluated from `(flag & 4) == 0`. |
| `offset_x` | `int` | Horizontal offset in pixels relative to the region left. |
| `offset_y` | `int` | Vertical offset in pixels relative to the virtual canvas top. |
| `size_x` | `int` | Width of the panel in pixels. |
| `size_y` | `int` | Height of the panel in pixels. |

#### Python Example:
```python
import bpy
import my_engine

# Locate the 3D View N-Panel UI region
ui_region = next(r for a in bpy.context.screen.areas if a.type == 'VIEW_3D' 
                 for r in a.regions if r.type == 'UI')

# Extract all panels
panels = my_engine.get_region_panels(ui_region.as_pointer())
for p in panels:
    print(f"[{p['idname']}] '{p['label']}': size=({p['size_x']}x{p['size_y']}), open={p['is_open']}")

# Filter for a specific panel by label or idname
my_panels = my_engine.get_region_panels(ui_region.as_pointer(), target_name="Custom GPU Engine")
```

---

### 2. `get_active_category`

Returns the identifier of the active tab in the region's sidebar category bar.

```python
my_engine.get_active_category(region_ptr: int) -> str
```

#### Parameters:
- **`region_ptr`** (`int`): The native memory address of the region (`region.as_pointer()`).

#### Return Value:
- `str`: The tab name currently active (e.g., `"My Engine"`, `"Item"`, `"Tool"`, `"View"`). Returns `""` if no tab is active or the region pointer is invalid.

#### Python Example:
```python
import bpy
import my_engine

ui_region = next(r for a in bpy.context.screen.areas if a.type == 'VIEW_3D' 
                 for r in a.regions if r.type == 'UI')

active_tab = my_engine.get_active_category(ui_region.as_pointer())
if active_tab == "My Engine":
    print("User is viewing our custom add-on tab!")
```

---

### 3. `get_region_scroll`

Returns the View2D visible canvas boundaries and scroll offsets.

```python
my_engine.get_region_scroll(region_ptr: int) -> dict[str, float]
```

#### Parameters:
- **`region_ptr`** (`int`): The native memory address of the region (`region.as_pointer()`).

#### Return Value:
Returns a dictionary containing the `rctf` coordinates of `v2d.cur`:

| Key | Type | Description |
|---|---|---|
| `cur_xmin` | `float` | Minimum horizontal visible coordinate. |
| `cur_ymin` | `float` | Minimum vertical visible coordinate. |
| `cur_xmax` | `float` | Maximum horizontal visible coordinate. |
| `cur_ymax` | `float` | Maximum vertical visible coordinate (tracks vertical scroll). |

Returns an empty dictionary `{}` if `region_ptr` is `0` or memory read fails.

#### Python Example:
```python
import bpy
import my_engine

ui_region = next(r for a in bpy.context.screen.areas if a.type == 'VIEW_3D' 
                 for r in a.regions if r.type == 'UI')

scroll = my_engine.get_region_scroll(ui_region.as_pointer())
print(f"Scroll Y-Max: {scroll.get('cur_ymax', 0.0)}")
```

---

## Coordinate Space & Transformation Math

### Blender UI vs. GPU Viewport Coordinates

When drawing inside Blender with `gpu` / `gpu_extras` on a draw handler registered to `'UI'` at `'POST_PIXEL'`:
- **GPU Drawing Origin `(0, 0)`**: Located at the **bottom-left** of the sidebar region.
- **Blender DNA Panel Layout**:
  - Origin `(0, 0)` is at the **top-left** of the virtual scrollable canvas.
  - `offset_y` is negative as panels stack down.
  - `cur_ymax` shifts when the user scrolls through the N-panel.

```
Region Top -------------------------------------------- (Y = region.height)
|                                                     |
|   Panel offset_y is measured downward               |
|                                                     |
|   +-----------------------+                         |
|   | Panel Top:            |                         |
|   | y = height + offset_y - scroll_ymax             |
|   |                       |                         |
|   | (size_x, size_y)      |                         |
|   +-----------------------+                         |
|                                                     |
Region Bottom ----------------------------------------- (Y = 0)
(X = 0)                                               (X = region.width)
```

### Transformation Formula

To calculate the exact bottom-left corner `(x, y)` for GPU geometry rendering:

$$\text{screen\_x} = \text{offset\_x}$$

$$\text{screen\_y} = \text{ui\_region.height} + \text{offset\_y} - \text{scroll.get('cur\_ymax', 0)}$$

$$\text{width} = \text{size\_x}, \quad \text{height} = \text{size\_y}$$

```python
def get_screen_bounds(ui_region, panel_dict, scroll_dict):
    x = panel_dict['offset_x']
    y = ui_region.height + panel_dict['offset_y'] - scroll_dict.get('cur_ymax', 0)
    w = panel_dict['size_x']
    h = panel_dict['size_y']
    return x, y, w, h
```

> [!NOTE]
> Always register draw handlers on the **`'UI'` region**, not the `'WINDOW'` region. Registering on `'UI'` automatically makes `(0, 0)` relative to the sidebar, avoiding complex and fragile area-offset calculations.

---

## Build & Compilation Guide

### Prerequisites

1. **Operating System**: Windows 10/11 x64.
2. **C++ Compiler**: Microsoft Visual C++ (MSVC) supporting C++17 (Visual Studio 2022 or Build Tools).
3. **Python**: Python 3.13 (or matching your target Blender version: Python 3.10 for Blender 3.3-3.6, Python 3.11 for Blender 4.0-4.2, Python 3.13 for Blender 4.3+).
4. **Pybind11**: Installed in the active build environment (`pip install pybind11`).
5. **Blender DNA Headers**: Extracted headers from Blender source code:
   - `source/blender/makesdna`
   - `intern/guardedalloc`
   - `source/blender/blenlib`

### Setup Script (`setup.py`)

The compilation is managed via `setuptools` and `pybind11.setup_helpers`:

```python
import os
from setuptools import setup
from pybind11.setup_helpers import Pybind11Extension, build_ext

BLENDER_BASE = r"C:\Users\Just\Documents\cpp_bind\blender-main\blender-main"

ext_modules = [
    Pybind11Extension(
        "my_engine",
        ["my_engine.cpp"],
        include_dirs=[
            os.path.join(BLENDER_BASE, r"source\blender\makesdna"),
            os.path.join(BLENDER_BASE, r"intern\guardedalloc"),
            os.path.join(BLENDER_BASE, r"source\blender\blenlib"),
        ],
        cxx_std=17,
        extra_compile_args=["/O2", "/std:c++17"],
    ),
]

setup(
    name="my_engine",
    version="1.0.0",
    ext_modules=ext_modules,
    cmdclass={"build_ext": build_ext},
)
```

### Compilation Step

Open a terminal or PowerShell prompt configured with MSVC Build Tools:

```powershell
# Navigate to the compile directory
cd Cpp_compile

# Build the in-place extension
python setup.py build_ext --inplace
```

This generates `my_engine.cp313-win_amd64.pyd` (or corresponding Python ABI tag). Copy or move this binary into the root of your Blender add-on folder.

---

## Integration Guide & Example Usage

Here is a complete end-to-end example demonstrating how `my_engine` is used to draw a GPU rectangle directly over a panel:

```python
import bpy
import gpu
from gpu_extras.batch import batch_for_shader

# 1. Import my_engine
try:
    from . import my_engine
    HAS_ENGINE = True
except ImportError:
    import my_engine
    HAS_ENGINE = True

class GpuPanelOverlay:
    def __init__(self):
        self.shader = gpu.shader.from_builtin('UNIFORM_COLOR')
        self.draw_handle = None

    def get_ui_region(self):
        for window in bpy.context.window_manager.windows:
            for area in window.screen.areas:
                if area.type == 'VIEW_3D':
                    for region in area.regions:
                        if region.type == 'UI' and region.width > 1:
                            return region
        return None

    def draw_callback(self):
        ui_region = self.get_ui_region()
        if not ui_region:
            return

        # Check if our tab is selected
        if my_engine.get_active_category(ui_region.as_pointer()) != "My Engine":
            return

        # Retrieve panels and scroll data
        panels = my_engine.get_region_panels(ui_region.as_pointer())
        scroll = my_engine.get_region_scroll(ui_region.as_pointer())

        for p in panels:
            if p['label'] == "Custom GPU Engine" and p['is_open']:
                # Calculate screen bounds
                x = p['offset_x']
                y = ui_region.height + p['offset_y'] - scroll.get('cur_ymax', 0)
                w = p['size_x']
                h = p['size_y']

                # Draw a translucent overlay quad
                vertices = ((x, y), (x + w, y), (x + w, y + h), (x, y + h))
                indices = ((0, 1, 2), (2, 3, 0))
                batch = batch_for_shader(self.shader, 'TRIS', {"pos": vertices}, indices=indices)

                gpu.state.blend_set('ALPHA')
                self.shader.uniform_float("color", (0.1, 0.5, 0.8, 0.4))
                batch.draw(self.shader)
                gpu.state.blend_set('NONE')

    def start(self):
        if self.draw_handle is None:
            self.draw_handle = bpy.types.SpaceView3D.draw_handler_add(
                self.draw_callback, (), 'UI', 'POST_PIXEL'
            )

    def stop(self):
        if self.draw_handle is not None:
            bpy.types.SpaceView3D.draw_handler_remove(self.draw_handle, 'UI')
            self.draw_handle = None
```

---

## Cross-Platform Portability

Currently, `my_engine` is targeted for **Windows (x64)** using `<windows.h>` and `ReadProcessMemory`.

To compile and run on Linux or macOS, substitute `safe_mem_read` with platform-specific memory APIs:

### Linux (`process_vm_readv`)
```cpp
#include <sys/uio.h>
#include <unistd.h>

bool safe_mem_read(const void* target_address, void* local_buffer, size_t size) {
    if (target_address == nullptr) return false;
    struct iovec local = { local_buffer, size };
    struct iovec remote = { const_cast<void*>(target_address), size };
    ssize_t nread = process_vm_readv(getpid(), &local, 1, &remote, 1, 0);
    return (nread == static_cast<ssize_t>(size));
}
```

### macOS (`vm_read_overwrite`)
```cpp
#include <mach/mach.h>
#include <mach/vm_map.h>

bool safe_mem_read(const void* target_address, void* local_buffer, size_t size) {
    if (target_address == nullptr) return false;
    vm_size_t bytes_read = 0;
    kern_return_t kr = vm_read_overwrite(
        mach_task_self(),
        reinterpret_cast<vm_address_t>(target_address),
        size,
        reinterpret_cast<vm_address_t>(local_buffer),
        &bytes_read
    );
    return (kr == KERN_SUCCESS && bytes_read == size);
}
```

---

## Troubleshooting & FAQs

### Q: `ImportError: DLL load failed while importing my_engine`
**Cause**: The compiled `.pyd` architecture or Python version does not match Blender's embedded Python.
**Fix**: Verify that the Python version used to build matches Blender (`bpy.app.version`). Run `python setup.py build_ext --inplace` using the exact Python executable or virtual environment configured with Blender's Python minor version.

### Q: `get_region_panels` returns an empty list
**Cause**: The N-Panel sidebar is hidden (collapsed to 0 width) or the `region_ptr` belongs to a non-UI region.
**Fix**: Ensure `ui_region.width > 1`. In Blender, an N-panel sidebar that is closed has a width of 0 or 1.

### Q: Coordinates appear offset after scrolling
**Cause**: Scroll offsets were not subtracted from the vertical position.
**Fix**: Ensure `scroll.get('cur_ymax', 0)` is subtracted:
`y = ui_region.height + p['offset_y'] - scroll.get('cur_ymax', 0)`.

### Q: Blender crashes after updating Blender to a new major release
**Cause**: Internal DNA struct layouts (`ARegion`, `Panel`, `View2D`) changed member offsets between Blender releases.
**Fix**: Update the DNA header files in your build directory from the target Blender source release and recompile `my_engine.cpp`.
