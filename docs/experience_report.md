# Experience Report: Custom GPU UI Panel Overlays in Blender

This document summarizes the technical design, issues encountered, and best practices discovered while building a custom GPU panel overlay for rendering active model previews.

---

## What We Built
The goal was to render viewport screenshots of selected/active Blender models inside a sidebar panel using a custom C++ library (`my_engine`) that queries panel locations, combined with Blender's GPU drawing APIs.

1. **Standalone Panel Class**: A top-level collapsible sidebar panel (`Custom GPU Engine`) was added in `panels.py` with empty vertical spacer columns to reserve viewport screen area.
2. **GPU Texture Rendering**: Blender objects were captured using `ViewportCapture` as PNG bytes, loaded as packed Blender Images, converted to GPU textures (`gpu.texture.from_image`), and rendered onto a 2D batch in the viewport.
3. **Region-Specific Draw Handler**: A draw callback was registered to the `'UI'` region at the `'POST_PIXEL'` stage using `bpy.types.SpaceView3D.draw_handler_add`.

---

## Issues & Bottlenecks Encountered

### 1. Viewport vs. UI Coordinate Spaces
* **Issue**: When registering a draw handler on the `'WINDOW'` region, coordinates are relative to the entire 3D Viewport. Drawing over a sidebar panel requires manually querying and adding the sidebar region's offsets (`ui_region.x`, `ui_region.y`), which is error-prone and scales poorly.
* **Solution**: Registering the draw handler on the **`'UI'` region** directly places the coordinate system origin `(0, 0)` at the bottom-left of the sidebar itself, eliminating the need for window-relative offsets.

### 2. Panel Coordinate Alignment (Top vs. Bottom)
* **Issue**: Blender UI panels are computed from the top of the region down, so the C++ library returns the y-coordinate of the **top** of the panel. Standard GPU geometry draws from bottom-left up. Drawing with `win_y = y - h` shifted the layout completely below the panel boundaries.
* **Solution**: The base y-coordinate for the rectangle should be kept at `win_y = y`, and geometry drawn from `y` to `y + h`.

### 3. Rendering-Induced UI Stutter
* **Issue**: Generating a preview screenshot uses the EEVEE renderer (`bpy.ops.render.render`), which runs on Blender's main thread and blocks all user input. Sequentially rendering multiple angles or batch selections resulted in a freeze of up to 1 second per selection change.
* **Solution**: Live previews should strictly render only **one single viewport angle** at a lightweight resolution (e.g. `128x128` or `256x256`). Additionally, a toggle checkbox (e.g. "Auto Capture Previews") and a manual **"Refresh Preview"** button should be provided to allow the user to modeling without interruptions.

### 4. API Suffix Deprecations (`blf.size`)
* **Issue**: Blender 5.0+ deprecated and removed the third DPI argument from the `blf` text size function, resulting in a `TypeError: blf.size() takes exactly 2 arguments (3 given)` when running `blf.size(font, size, dpi)`.
* **Solution**: Use the updated 2-argument signature `blf.size(font_id, size)` in modern versions of Blender.

---

## Best Practices for Similar Features

> [!TIP]
> **1. Prioritize Main-Thread Performance**
> Avoid background-rendering multi-angle captures or large viewport resolutions. Keep previews to single-frame captures and cap resolutions at `128x128` for instantaneous drawing.

> [!IMPORTANT]
> **2. Implement Manual Refresh Controls**
> Live background rendering during rapid viewport modeling is a major source of lag. Always default to manual refresh buttons or provide an "Auto Capture" toggle.

> [!NOTE]
> **3. Leverage Local Region Binding**
> Bind draw handlers to specific UI or region containers (like `'UI'`) rather than the broad `'WINDOW'` space. This simplifies coordinate calculations and prevents issues with window resizing.

> [!WARNING]
> **4. Watch out for Blender API Changes**
> The Blender Python API (specifically `gpu`, `bgl`, and `blf`) is updated frequently. Always query the active version (`bpy.app.version`) and wrap version-sensitive methods inside conditional fallbacks.
