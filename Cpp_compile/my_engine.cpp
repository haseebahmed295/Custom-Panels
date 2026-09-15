#include <pybind11/pybind11.h>
#include <windows.h> 
#include <string>

#include "DNA_vec_types.h"
#include "DNA_ID.h"
#include "DNA_listBase.h"
#include "DNA_view2d_types.h"
#include "DNA_screen_types.h"

namespace py = pybind11;
using namespace blender;

bool safe_mem_read(const void* target_address, void* local_buffer, size_t size) {
    if (target_address == nullptr) return false;
    SIZE_T bytes_read = 0;
    return (ReadProcessMemory(GetCurrentProcess(), target_address, local_buffer, size, &bytes_read) && bytes_read == size);
}


std::string get_active_category(uintptr_t region_ptr) {
    if (region_ptr == 0) return "";
    
    ARegion local_region;
    if (!safe_mem_read(reinterpret_cast<const void*>(region_ptr), &local_region, sizeof(ARegion))) {
        return ""; 
    }

    // Check if there are any active categories
    if (local_region.panels_category_active.first == nullptr) {
        return "";
    }

    // Read the first item in the stack, which is the currently active tab
    PanelCategoryStack active_category;
    if (!safe_mem_read(local_region.panels_category_active.first, &active_category, sizeof(PanelCategoryStack))) {
        return "";
    }
    
    return std::string(active_category.idname);
}
py::dict get_region_scroll(uintptr_t region_ptr) {
    py::dict result;
    if (region_ptr == 0) return result;

    ARegion local_region;
    if (!safe_mem_read(reinterpret_cast<const void*>(region_ptr), &local_region, sizeof(ARegion))) {
        return result; 
    }

    // v2d.cur represents the exact rectangle of the virtual canvas currently visible on screen
    result["cur_xmin"] = local_region.v2d.cur.xmin;
    result["cur_ymin"] = local_region.v2d.cur.ymin;
    result["cur_xmax"] = local_region.v2d.cur.xmax;
    result["cur_ymax"] = local_region.v2d.cur.ymax;

    return result;
}
void extract_panels_recursive(Panel* p, py::list& out_list, int parent_x, int parent_y) {
    if (!p) return;

    Panel local_panel;
    if (!safe_mem_read(p, &local_panel, sizeof(Panel))) return;

    int absolute_x = parent_x + local_panel.ofsx;
    int absolute_y = parent_y + local_panel.ofsy;

    py::dict py_panel;
    
    // 1. The Internal ID Name
    py_panel["idname"] = py::str(local_panel.panelname);

    // 2. The UI Label (drawname)
    char label_buffer[256] = {0};
    if (local_panel.drawname && safe_mem_read(local_panel.drawname, label_buffer, 255)) {
        py_panel["label"] = py::str(label_buffer);
    } else {
        py_panel["label"] = py::str(""); // Some layout panels don't have titles
    }
    
    py_panel["is_open"] = py::bool_(((local_panel.flag & 4) == 0));
    py_panel["offset_x"] = absolute_x;
    py_panel["offset_y"] = absolute_y;
    py_panel["size_x"] = local_panel.sizex;
    py_panel["size_y"] = local_panel.sizey;
    out_list.append(py_panel);

    Panel* child = reinterpret_cast<Panel*>(local_panel.children.first);
    while (child) {
        extract_panels_recursive(child, out_list, absolute_x, absolute_y);
        
        Panel next_child;
        safe_mem_read(child, &next_child, sizeof(Panel));
        child = reinterpret_cast<Panel*>(next_child.next);
    }
}

py::list get_region_panels(uintptr_t region_ptr, std::string target_name) {
    py::list panel_list;
    if (region_ptr == 0) return panel_list;

    ARegion local_region;
    if (!safe_mem_read(reinterpret_cast<const void*>(region_ptr), &local_region, sizeof(ARegion))) {
        return panel_list; 
    }

    Panel* current_panel_ptr = reinterpret_cast<Panel*>(local_region.panels.first);
    int safety_counter = 0; 
    
    while (current_panel_ptr != nullptr && safety_counter < 500) {
        Panel local_panel;
        if (!safe_mem_read(current_panel_ptr, &local_panel, sizeof(Panel))) break;
        
        char label_buffer[256] = {0};
        std::string panel_label = "";
        if (local_panel.drawname && safe_mem_read(local_panel.drawname, label_buffer, 255)) {
            panel_label = std::string(label_buffer);
        }
        
        std::string panel_idname = std::string(local_panel.panelname);
        
        // If target_name is empty, grab EVERYTHING. 
        // Otherwise, match against the ID Name or the UI Label.
        if (target_name == "" || panel_label == target_name || panel_idname == target_name) {
            extract_panels_recursive(current_panel_ptr, panel_list, 0, 0);
        }
        
        current_panel_ptr = reinterpret_cast<Panel*>(local_panel.next);
        safety_counter++;
    }
    return panel_list;
}

PYBIND11_MODULE(my_engine, m) {
    m.def("get_region_panels", &get_region_panels, py::arg("region_ptr"), py::arg("target_name") = "");
    m.def("get_active_category", &get_active_category, py::arg("region_ptr"));
    
    // Bind the new scroll function
    m.def("get_region_scroll", &get_region_scroll, py::arg("region_ptr"), "Get View2D scroll offsets");
}