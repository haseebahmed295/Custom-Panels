import bpy

MODEL_TIMER_INTERVAL = 0.1

class EventHandler(bpy.types.Operator):
    """Event Handler for the Custom GPU Panel Engine"""
    bl_idname = "gpu.panel_handler"
    bl_label = "Custom GPU Event Handler"
    bl_options = {'REGISTER'}

    _timer = None

    def modal(self, context, event):
        if context.scene.gpu_event_handler_state == False:
            self.cancel(context)
            # self.report({'INFO'}, "Modal Killed")
            return {'CANCELLED'}

        process = self.handle_timer_event(context, event)
        if process == 'PASS_THROUGH':
            return {'PASS_THROUGH'}
        elif process == 'RUNNING_MODAL':
            return {'RUNNING_MODAL'}
        elif process in ('CANCELLED', 'FINISHED'):
            self.cancel(context)
            return {process}
        else:
            return {'PASS_THROUGH'}

    def execute(self, context):
        wm = context.window_manager
        self._timer = wm.event_timer_add(MODEL_TIMER_INTERVAL, window=context.window)
        wm.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def cancel(self, context):
        wm = context.window_manager
        wm.event_timer_remove(self._timer)

    def handle_timer_event(self, context, event):
        # Pass input data to your ui_elements framework here later
        if event.type in {'MOUSEMOVE', 'LEFTMOUSE', 'RIGHTMOUSE'}:
            pass
            
        return "PASS_THROUGH"