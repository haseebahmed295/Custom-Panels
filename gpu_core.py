import bpy
import gpu

try:
    from . import my_engine
    HAS_ENGINE = True
except ImportError:
    HAS_ENGINE = False
    print("WARNING: 'my_engine' module not found. GPU overlay will not work.")

TIMER_INTERVAL = 0.2
draw_handle = None

class GpuDrawManager:
    def __init__(self):
        pass

    @staticmethod
    def get_3d_view_ui_region():
        if not bpy.context.window_manager: return None
        for window in bpy.context.window_manager.windows:
            for area in window.screen.areas:
                if area.type == 'VIEW_3D':
                    for region in area.regions:
                        if region.type == 'UI':
                            return region
        return None

    @staticmethod
    def is_panel_active():
        if not HAS_ENGINE: return False
        
        ui_region = GpuDrawManager.get_3d_view_ui_region()
        if not ui_region or ui_region.width <= 1: 
            return False
            
        active_tab = my_engine.get_active_category(ui_region.as_pointer())
        return active_tab == "My Engine"

    @staticmethod
    def tag_redraw_all_3d_views():
        if not bpy.context.window_manager: return
        for window in bpy.context.window_manager.windows:
            for area in window.screen.areas:
                if area.type == 'VIEW_3D':
                    area.tag_redraw()

    @staticmethod
    def get_panel_dimensions():
        if not HAS_ENGINE: return []
        
        ui_region = GpuDrawManager.get_3d_view_ui_region()
        if not ui_region: return []
        
        panels = my_engine.get_region_panels(ui_region.as_pointer())
        scroll = my_engine.get_region_scroll(ui_region.as_pointer())
        
        panel_data = []
        for p in panels:
            x = p['offset_x']
            y = ui_region.height + p['offset_y'] - scroll.get('cur_ymax', 0)
            w = p['size_x']
            h = p['size_y']
            panel_data.append((x, y, w, h, p['label'], p['is_open']))
        
        return panel_data

    def draw_panel_boxes(self):
        if not HAS_ENGINE: return

        panels = GpuDrawManager.get_panel_dimensions()
        
        gpu.state.blend_set('ALPHA')
        for panel in panels:
            x, y, w, h, label, is_open = panel
            print(panel)
            if label == "Custom GPU Engine" and is_open:
                # Draw Here
                pass
            
        gpu.state.blend_set('NONE')


# --- Global Lifecycle Management ---

def watchdog_timer_check():
    """Runs continuously to mount/unmount the GPU handler and Modals."""
    global draw_handle
    panel_active = GpuDrawManager.is_panel_active()
    
    # STATE 1: Panel Open, Handler Missing -> START IT UP
    if panel_active and draw_handle is None:
        manager = GpuDrawManager()
        draw_handle = bpy.types.SpaceView3D.draw_handler_add(
            manager.draw_panel_boxes, (), 'UI', 'POST_PIXEL'
        )

        if not bpy.context.scene.gpu_event_handler_state:
            bpy.ops.gpu.panel_handler('INVOKE_DEFAULT')
            bpy.context.scene.gpu_event_handler_state = True

        GpuDrawManager.tag_redraw_all_3d_views()
        
    # STATE 2: Panel Closed, Handler Running -> TEAR IT DOWN
    elif not panel_active and draw_handle is not None:
        teardown_draw_handler()
        GpuDrawManager.tag_redraw_all_3d_views()
        
    return TIMER_INTERVAL

def teardown_draw_handler():
    global draw_handle
    if draw_handle is not None:
        bpy.context.scene.gpu_event_handler_state = False
        bpy.types.SpaceView3D.draw_handler_remove(draw_handle, 'UI')
        draw_handle = None