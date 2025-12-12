import dearpygui.dearpygui as dpg

dpg.create_context()

# Initial panel widths
left_width = 180
right_width = 180

def update_layout():
    # Get total window content width
    window_width = dpg.get_item_width("main_window")

    # Calculate remaining space for center
    center_width = window_width - dpg.get_item_width("left_panel") - dpg.get_item_width("right_panel") - 40
    center_width = max(center_width, 100)

    dpg.set_item_width("center_panel", center_width)

def resize_left(sender, app_data, user_data):
    new_width = max(80, left_width + app_data)
    dpg.set_item_width("left_panel", new_width)
    update_layout()

def resize_right(sender, app_data, user_data):
    new_width = max(80, right_width - app_data)
    dpg.set_item_width("right_panel", new_width)
    update_layout()

with dpg.window(tag="main_window", label="Resizable Layout", width=1000, height=600, no_scrollbar=True, no_collapse=True):

    with dpg.group(horizontal=True):

        # LEFT PANEL
        with dpg.child_window(tag="left_panel", width=left_width, border=True):
            with dpg.tree_node(label="Left Tree", default_open=True):
                dpg.add_text("Left Item 1")
                dpg.add_text("Left Item 2")

        # DRAG HANDLE LEFT
        dpg.add_drag_float(label="↔", width=10, default_value=0, min_value=-500, max_value=500, callback=resize_left)

        # CENTER PANEL (dynamic width)
        with dpg.child_window(tag="center_panel", border=True):
            with dpg.table(header_row=True, resizable=True, borders_innerH=True, borders_innerV=True,
                           policy=dpg.mvTable_SizingStretchProp, scrollX=True, scrollY=True):
                dpg.add_table_column(label="Column 1")
                dpg.add_table_column(label="Column 2")
                dpg.add_table_column(label="Column 3")
                for i in range(10):
                    with dpg.table_row():
                        dpg.add_text(f"Row {i} - 1")
                        dpg.add_text(f"Row {i} - 2")
                        dpg.add_text(f"Row {i} - 3")

        # DRAG HANDLE RIGHT
        dpg.add_drag_float(label="↔", width=10, default_value=0, min_value=-500, max_value=500, callback=resize_right)

        # RIGHT PANEL
        with dpg.child_window(tag="right_panel", width=right_width, border=True):
            with dpg.tree_node(label="Right Tree", default_open=True):
                dpg.add_text("Right Item A")
                dpg.add_text("Right Item B")

# On resize, adjust layout
def on_resize(sender, app_data):
    update_layout()

dpg.set_viewport_resize_callback(on_resize)

dpg.create_viewport(title="Resizable Panels App", width=1000, height=600)
dpg.setup_dearpygui()
dpg.show_viewport()
update_layout()
dpg.start_dearpygui()
dpg.destroy_context()

