
import dearpygui.dearpygui as dpg
import xml.etree.ElementTree as ET

DIAGNOSTIC_WORDS = ["idiagnostic1", "idiagnostic2", "idiagnostic3"]
DIAG_TYPES = ["UF", "UW", "UM", "SF"]
USER_DIAG_TEXTS = [f"{dt}_{i:02d}" for dt in DIAG_TYPES for i in range(64)]

class App:
    def __init__(self):
        self._keep_alive = True
        self.instances = {} # Dict with loaded AOI instances
        self.AOIs = {}      # Dict with loaded AOI definitions
        self.current_instance = None

    def exit_app(self, sender):
        self._keep_alive = False
    
    def select_file(self, sender):
        fs = dpg.add_file_dialog(directory_selector=False, show=True, 
                                 tag="file_dialog_id", width=700 ,height=400,
                                 callback=self.load)
        dpg.add_file_extension(extension=".L5X,.l5x", parent=fs)
    
    def node_selected(self, sender):  
        # Unselect other instances and select actual
        children = dpg.get_item_children("Instances", 1)  # 1 = slot for items
        if children:
            for child in children:
                dpg.set_value(child, False)
        dpg.set_value(sender, True)
        # Display corresponding diagnostics and remember selection
        self.clear_diagnostics()
        for ins_name, ins_data in self.instances.items():
            if ins_data["tree_node"] == sender:
                self.current_instance = ins_name
                self.display_diagnostics(ins_name)
                break
    
    def clear_diagnostics(self):
        children = dpg.get_item_children("diag_table", 1)  # 1 = slot for items
        if children:
            for child in children:
                dpg.delete_item(child)
    
    def display_diagnostics(self, ins_name):
        # AOI Diagnostics
        diag_aoi = self.AOIs[self.instances[ins_name]["datatype"]].copy()
        # Local Diagnostics
        diag_local = self.get_instance_diagnostics(self.instances[ins_name]["XML_node"])
        # Populate table
        for diag, texts_aoi in diag_aoi.items():
            for lan, text_aoi in texts_aoi.items():
                with dpg.table_row(parent="diag_table") as row:
                    dpg.add_text(diag)
                    dpg.add_text(lan)
                    text_local = diag_local[diag][lan] if diag in diag_local else ""
                    dpg.add_text(text_local)
                    dpg.add_text(text_aoi) 
                    color = [255,255,255,255]
                    if text_local != text_aoi:
                        if text_local == "":
                            color = [255,165,0,255]
                        elif text_aoi not in USER_DIAG_TEXTS or text_local[:2] != text_aoi[:2]:
                            color = [200,0,0,255]
                    with dpg.theme() as theme_id:
                        with dpg.theme_component(0):
                            dpg.add_theme_color(dpg.mvThemeCol_Text, color, category=dpg.mvThemeCat_Core)
                        dpg.bind_item_theme(row, theme_id)

    def load_AOIs(self, xml_root):
        res = {}
        AOI_elements = xml_root.iter("AddOnInstructionDefinition")
        for elem in AOI_elements:
            AOI_name = elem.attrib.get("Name")
            for param in elem.find("Parameters"):
                if param.attrib.get("Name") == "cDeviceID" and AOI_name != "MCP_Device":
                    res[AOI_name] = {}
                    break
            if AOI_name in res:
                for param in elem.find("Parameters"): 
                    AOI_diag_word = param.attrib.get("Name")
                    if AOI_diag_word.lower() in DIAGNOSTIC_WORDS:
                        for comment in param.find("Comments"):
                            operand = comment.attrib.get("Operand")
                            texts = {}
                            for loc_comm in comment.findall("LocalizedComment"):
                                lan = loc_comm.attrib.get("Lang")
                                text = loc_comm.text.replace("\n", "")
                                if lan in ["en-GB", "sv-SE"]:   
                                    texts[lan] = text             
                            res[AOI_name][f"{AOI_diag_word.lower()}{operand}"] = texts
        return res

    def load_instances(self, xml_root):
        res = {}
        for tag in xml_root.find("Controller").find("Tags"):
            if tag.attrib.get("DataType") in self.AOIs:
                ins_name = tag.attrib.get("Name")
                res[ins_name] = {
                    "datatype": tag.attrib.get("DataType"),
                    "XML_node": tag,
                    "tree_node": 0,
                }
        return res

    def get_instance_diagnostics(self, xml_node):
        res = {}
        comments = xml_node.find("Comments")
        if comments is not None:
            for comment in comments.findall("Comment"):
                diag = comment.attrib.get("Operand").lower()[1:]
                if any(word in diag for word in DIAGNOSTIC_WORDS):
                    texts = {"en-GB": "", "sv-SE": ""}
                    for loc_comm in comment.findall("LocalizedComment"):
                        lan = loc_comm.attrib.get("Lang")
                        text = loc_comm.text.replace("\n", "")
                        if lan in ["en-GB", "sv-SE"]:   
                            texts[lan] = text             
                    res[diag] = texts
        return res  

    def update_layout(self):
        # Get total window content width
        window_width = dpg.get_item_width(self._window)
        # Calculate remaining space for center
        center_width = window_width - dpg.get_item_width("left_panel") - dpg.get_item_width("right_panel") - 40
        center_width = max(center_width, 100)
        dpg.set_item_width("center_panel", center_width)

    def resize_left(self, sender, app_data, user_data):
        new_width = max(80, 200 + app_data)
        dpg.set_item_width("left_panel", new_width)
        self.update_layout()

    def resize_right(self, sender, app_data, user_data):
        new_width = max(80, 200 - app_data)
        dpg.set_item_width("right_panel", new_width)
        self.update_layout()

    def load(self, sender, file_data):
        file_path = file_data['file_path_name']
        try:
            tree = ET.parse(file_path)
            xml_root = tree.getroot()
            self.AOIs = self.load_AOIs(xml_root)
            self.instances = self.load_instances(xml_root)
            self.draw_layout()
        except Exception as e:
            print("Error loading file:", e)
            return

    def draw_layout(self):
        with dpg.group(horizontal=True, parent=self._window):
            # INSTANCE PANEL
            with dpg.child_window(tag="left_panel", width=200, border=True):
                with dpg.tree_node(tag="Instances", label="Instances", default_open=True):
                    for (name, value) in self.instances.items():
                        instance_node = dpg.add_selectable(label=f"{name} ({value["datatype"]})", callback=self.node_selected)
                        self.instances[name]["tree_node"] = instance_node
            # DRAG HANDLE LEFT
            dpg.add_drag_float(label="", width=10, default_value=0, min_value=-500, max_value=500, callback=self.resize_left)
            # CENTRAL PANEL
            with dpg.child_window(tag="center_panel", border=True):
                # Button bar above the diagnostics table
                with dpg.group(horizontal=True):
                    dpg.add_button(label="Fix", callback=self.fix_diagnostics)
                    dpg.add_button(label="Save", callback=self.save_diagnostics)
                with dpg.table(tag="diag_table", header_row=True, resizable=True, borders_innerH=True, borders_innerV=True, policy=dpg.mvTable_SizingStretchProp):
                    dpg.add_table_column(label="Diagnostic")
                    dpg.add_table_column(label="Language")
                    dpg.add_table_column(label="Local Description")
                    dpg.add_table_column(label="AOI Description")
            # SPLITTER BAR 2
            dpg.add_drag_float(label="", width=10, default_value=0, min_value=-500, max_value=500, callback=self.resize_right)
            # AOI PANEL
            with dpg.child_window(tag="right_panel", width=200, border=True):
                with dpg.tree_node(label="AOIs", default_open=True):
                    for aoi in self.AOIs.keys():
                        dpg.add_text(aoi) 
        self.update_layout()

    def run(self):
        dpg.create_context()
        # WINDOW
        self._window = dpg.add_window(tag="Primary Window", label="Example Window")
        # MAIN MENU
        with dpg.menu_bar(parent=self._window):
            with dpg.menu(label="Main"):
                dpg.add_menu_item(label="Load", callback=self.select_file)
                dpg.add_menu_item(label="Save")
                dpg.add_separator()
                dpg.add_menu_item(label="Exit", callback=self.exit_app)
            with dpg.menu(label="Help"):
                dpg.add_menu_item(label="Help")
                dpg.add_separator()
                dpg.add_menu_item(label="About", callback=self.test)
        dpg.create_viewport(title='Simumatik Co-Sim', width=800, height=640)
        dpg.setup_dearpygui()
        dpg.show_viewport()
        dpg.set_primary_window("Primary Window", True)
        # below replaces, start_dearpygui()
        while dpg.is_dearpygui_running() and self._keep_alive:
            # insert here any code you would like to run in the render loop
            # you can manually stop by using stop_dearpygui()
            dpg.render_dearpygui_frame()
        dpg.destroy_context()
        
    def save_callback(self, sender):
        print("Save Clicked")

    def fix_diagnostics(self, sender):
        """Refresh diagnostics for the currently selected instance."""
        pass

    def save_diagnostics(self, sender):
        """Placeholder: export diagnostics (not fully implemented)."""
        # Simple placeholder — extend to export table rows to CSV if desired
        pass


    # callback runs when user attempts to connect attributes
    def link_callback(self, sender, app_data):
        # app_data -> (link_id1, link_id2)
        dpg.add_node_link(app_data[0], app_data[1], parent=sender)

    # callback runs when user attempts to disconnect attributes
    def delink_callback(self, sender, app_data):
        # app_data -> link_id
        dpg.delete_item(app_data)

    def test(sender):
        print("sdadfas")

