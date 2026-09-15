bl_info = {
    "name": "Custom GPU Panel Engine",
    "author": "Your Name",
    "version": (1, 0, 0),
    "blender": (3, 0, 0),
    "location": "View3D > N-Panel > My Engine",
    "description": "Draws a custom GPU overlay inside the N-Panel",
    "warning": "Requires custom my_engine binary",
    "category": "3D View",
}

import bpy
from . import gpu_core
from . import event_handler

class CUSTOM_PT_gpu_canvas(bpy.types.Panel):
    bl_idname = "CUSTOM_PT_gpu_canvas"
    bl_label = "Custom GPU Engine"     
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'My Engine'          

    def draw(self, context):
        layout = self.layout
        col = layout.column()
        # Reserve 15 rows of height to make room for your GPU canvas
        col.scale_y = 15.0 
        col.label(text="")

classes = (
    CUSTOM_PT_gpu_canvas,
    event_handler.EventHandler,
)

def register(): 
    for cls in classes:
        bpy.utils.register_class(cls)
        
    bpy.types.Scene.gpu_event_handler_state = bpy.props.BoolProperty(default=False)

    # Register Watchdog
    if not bpy.app.timers.is_registered(gpu_core.watchdog_timer_check):
        bpy.app.timers.register(gpu_core.watchdog_timer_check)

def unregister():   
    # Unregister Watchdog
    if bpy.app.timers.is_registered(gpu_core.watchdog_timer_check):
        bpy.app.timers.unregister(gpu_core.watchdog_timer_check)
        
    gpu_core.teardown_draw_handler()

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
        
    if hasattr(bpy.types.Scene, "gpu_event_handler_state"):
        del bpy.types.Scene.gpu_event_handler_state

if __name__ == "__main__":
    register()