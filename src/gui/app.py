
import dearpygui.dearpygui as dpg
from lxml import etree

VERSION = "0.1.4"
LANGUAGES = ["en-GB", "sv-SE"]
DIAGNOSTIC_WORDS = ["idiagnostic1", "idiagnostic2", "idiagnostic3"]
DIAG_TYPES = ["UF", "UW", "UM", "SF", "SW", "SM"]
USER_DIAG_TEXTS = [f"{dt}_{i:02d}" for dt in DIAG_TYPES for i in range(64)]
COLOR_WHITE = [255,255,255,255]
COLOR_RED = [200,0,0,255]
COLOR_ORANGE = [255,165,0,255]
COLOR_PURPLE = [128,0,128,255]
STATUS_OK = "OK"
STATUS_ISSUE = "ISSUE"

class App:
    def __init__(self):
        self.clear()

    def clear(self):
        self._keep_alive = True
        self.instances = {} # Dict with loaded AOI instances
        self.instance_status = {} # Dict with instance diagnostic status
        self.AOIs = {}      # Dict with loaded AOI definitions
        self.current_instance = None
        self.editing = False
        self.edit_inputs = {}

    def exit_app(self, sender):
        self._keep_alive = False
    
    def select_load_file(self, sender):
        with dpg.file_dialog(directory_selector=False, show=True, width=700 ,height=400, callback=self.load_callback):
            dpg.add_file_extension(extension=".L5X,.l5x")    

    def select_save_file(self, sender):
        with dpg.file_dialog(directory_selector=False, show=True, width=700 ,height=400, callback=self.save_callback):
            dpg.add_file_extension(extension=".L5X,.l5x")
    
    def node_selected(self, sender):  
        # Unselect other instances and select actual
        children = dpg.get_item_children("Instances", 1)  # 1 = slot for items
        if children:
            for child in children:
                dpg.set_value(child, False)
        dpg.set_value(sender, True)
        # If editing, cancel first
        if self.editing:
            self.cancel_edits(None)
        # Display corresponding diagnostics and remember selection
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
    
    def display_diagnostics(self, ins_name, show_table=True):
        self.clear_diagnostics()
        if self.editing:
            self.edit_inputs = {}
        # AOI Diagnostics
        diag_aoi = self.AOIs[self.instances[ins_name]["datatype"]].copy()
        diag_aoi.pop("Revision", None)
        # Local Diagnostics
        diag_local = self.get_instance_diagnostics(self.instances[ins_name]["XML_node"])
        # Instance color
        instance_color = COLOR_WHITE
        # Populate table
        for diag, texts_aoi in diag_aoi.items():
            lans = list(texts_aoi.keys())
            if diag in diag_local:
                lans += list(diag_local[diag].keys())
            lans = set(lans)
            # Check if language description is consistent
            lan_desc_count = 0
            for lan in lans:
                if diag in diag_local:
                    if (diag_local[diag][lan] != texts_aoi.get(lan, "")) and (diag_local[diag][lan] != ""):
                        lan_desc_count += 1
            both_lan_exist = (lan_desc_count == len(lans)) or (lan_desc_count == 0)
            for lan in lans:
                text_local = diag_local[diag][lan] if diag in diag_local else ""
                text_aoi = texts_aoi.get(lan, "")
                color = COLOR_WHITE
                if lan not in LANGUAGES:
                    # Language not supported
                    color = COLOR_RED
                    instance_color = COLOR_RED
                # local text includes special character combination
                elif "<@" in text_local:
                    color = COLOR_RED
                    instance_color = COLOR_RED                        
                elif text_local != text_aoi:
                    # Both language descriptions do not exist
                    if not both_lan_exist:
                        color = COLOR_RED
                        instance_color = COLOR_RED
                    # Empty text. Text is going to be replaced with AOI text
                    elif text_local == "":
                        color = COLOR_ORANGE
                        instance_color = COLOR_ORANGE if instance_color != COLOR_RED else instance_color
                    # Not allowed diagnostic text, will be overwritten
                    elif text_aoi in ["DO NOT USE", "ANVÄND EJ"]:
                        color = COLOR_RED
                        instance_color = COLOR_RED
                    # User defined text in AOI specific bit
                    elif text_aoi[:2] not in DIAG_TYPES:
                        color = COLOR_RED
                        instance_color = COLOR_RED
                    # User defined text that differs from AOI type
                    elif text_aoi in USER_DIAG_TEXTS and text_local[:2] != text_aoi[:2]:
                        color = COLOR_RED
                        instance_color = COLOR_RED
                if show_table:
                    with dpg.table_row(parent="diag_table") as row:
                        dpg.add_text(diag)
                        dpg.add_text(lan)
                        if self.editing:
                            input_tag = f"input_{diag}_{lan}"
                            input_widget = dpg.add_input_text(default_value=text_local, tag=input_tag)
                            with dpg.popup(input_widget, mousebutton=dpg.mvMouseButton_Right, modal=False):
                                dpg.add_menu_item(label="Copy", callback=self.copy_text, user_data=input_tag)
                                dpg.add_menu_item(label="Paste", callback=self.paste_text, user_data=input_tag)
                                dpg.add_menu_item(label="Cut", callback=self.cut_text, user_data=input_tag)
                            self.edit_inputs[(diag, lan)] = input_tag
                        else:
                            dpg.add_text(text_local)
                        dpg.add_text(text_aoi) 
                    with dpg.theme() as theme_id:
                        with dpg.theme_component(0):
                            dpg.add_theme_color(dpg.mvThemeCol_Text, color, category=dpg.mvThemeCat_Core)
                        dpg.bind_item_theme(row, theme_id)
    
        # Mark Instance with color
        self.instance_status[ins_name] = STATUS_OK if instance_color != COLOR_RED else STATUS_ISSUE
        with dpg.theme() as theme_id:
            with dpg.theme_component(0):
                dpg.add_theme_color(dpg.mvThemeCol_Text, instance_color, category=dpg.mvThemeCat_Core)
            dpg.bind_item_theme(self.instances[ins_name]["tree_node"], theme_id)                

    def edit_diagnostics(self, sender):
        self.editing = True
        dpg.configure_item("edit_button", show=False)
        dpg.configure_item("save_button", show=True)
        dpg.configure_item("cancel_button", show=True)
        dpg.configure_item("copy_table_button", show=True)
        dpg.configure_item("copy_button", show=True)
        dpg.configure_item("paste_button", show=True)
        dpg.configure_item("replace_button", show=True)
        self.display_diagnostics(self.current_instance)

    def save_edits(self, sender):
        diag_local = {}
        for (diag, lan), tag in self.edit_inputs.items():
            text = dpg.get_value(tag)
            if diag not in diag_local:
                diag_local[diag] = {}
            diag_local[diag][lan] = text
        # Update XML
        xml_node = self.instances[self.current_instance]["XML_node"]
        comments = xml_node.find("Comments")
        if comments is None:
            comments = etree.SubElement(xml_node, "Comments")
        for diag, texts in diag_local.items():
            for comment in comments.findall("Comment"):
                if comment.attrib.get("Operand").lower()[1:] == diag:
                    for lan, text in texts.items():
                        for loc in comment.findall("LocalizedComment"):
                            if loc.attrib.get("Lang") == lan:
                                loc.text = etree.CDATA(text)
                                break
                        else:
                            etree.SubElement(comment, "LocalizedComment", {"Lang": lan}).text = etree.CDATA(text)
                    break
            else:
                comment = etree.SubElement(comments, "Comment", {"Operand": f".{diag}"})
                for lan, text in texts.items():
                    etree.SubElement(comment, "LocalizedComment", {"Lang": lan}).text = etree.CDATA(text)
        self.editing = False
        dpg.configure_item("edit_button", show=True)
        dpg.configure_item("save_button", show=False)
        dpg.configure_item("cancel_button", show=False)
        dpg.configure_item("copy_table_button", show=False)
        dpg.configure_item("copy_button", show=False)
        dpg.configure_item("paste_button", show=False)
        dpg.configure_item("replace_button", show=False)
        self.display_diagnostics(self.current_instance)

    def cancel_edits(self, sender):
        self.editing = False
        dpg.configure_item("edit_button", show=True)
        dpg.configure_item("save_button", show=False)
        dpg.configure_item("cancel_button", show=False)
        dpg.configure_item("copy_table_button", show=False)
        dpg.configure_item("copy_button", show=False)
        dpg.configure_item("paste_button", show=False)
        dpg.configure_item("replace_button", show=False)
        self.display_diagnostics(self.current_instance)

    def copy_column(self, sender):
        texts = [dpg.get_value(tag) for tag in self.edit_inputs.values()]
        clipboard_text = '\n'.join(texts)
        dpg.set_clipboard_text(clipboard_text)

    def copy_text(self, sender, app_data, user_data):
        """Copy text from input field to clipboard."""
        text = dpg.get_value(user_data)
        dpg.set_clipboard_text(text)

    def paste_text(self, sender, app_data, user_data):
        """Paste text from clipboard to input field."""
        clipboard_text = dpg.get_clipboard_text()
        if clipboard_text:
            dpg.set_value(user_data, clipboard_text)

    def cut_text(self, sender, app_data, user_data):
        """Cut text from input field to clipboard."""
        text = dpg.get_value(user_data)
        dpg.set_clipboard_text(text)
        dpg.set_value(user_data, "")

    def copy_table(self, sender):
        """Copy the entire diagnostics table to clipboard as tab-separated values."""
        table_data = []
        # Get all table rows
        children = dpg.get_item_children("diag_table", 1)  # 1 = slot for items (rows)
        if children:
            for row in children:
                row_data = []
                # Get children of the row (the cells)
                row_children = dpg.get_item_children(row, 1)
                if row_children:
                    for cell in row_children:
                        # Get the text value from each cell
                        if dpg.get_item_type(cell) == "mvAppItemType::mvText":
                            text = dpg.get_value(cell)
                        elif dpg.get_item_type(cell) == "mvAppItemType::mvInputText":
                            text = dpg.get_value(cell)
                        else:
                            text = ""
                        row_data.append(text)
                table_data.append("\t".join(row_data))
        
        # Join all rows with newlines
        clipboard_text = "\n".join(table_data)
        dpg.set_clipboard_text(clipboard_text)

    def paste_column(self, sender):
        clipboard_text = dpg.get_clipboard_text()
        lines = clipboard_text.split('\n')
        for i, tag in enumerate(self.edit_inputs.values()):
            if i < len(lines):
                dpg.set_value(tag, lines[i])

    def show_replace_popup(self, sender):
        with dpg.window(label="Replace Text", modal=True, tag="replace_popup", width=400, height=200):
            dpg.add_text("Find:")
            dpg.add_input_text(tag="find_input", width=350)
            dpg.add_text("Replace:")
            dpg.add_input_text(tag="replace_input", width=350)
            with dpg.group(horizontal=True):
                dpg.add_button(label="Cancel", callback=self.cancel_replace)
                dpg.add_button(label="Run", callback=self.run_replace)

    def cancel_replace(self, sender):
        dpg.delete_item("replace_popup")

    def run_replace(self, sender):
        find_text = dpg.get_value("find_input")
        replace_text = dpg.get_value("replace_input")
        for tag in self.edit_inputs.values():
            current_value = dpg.get_value(tag)
            new_value = current_value.replace(find_text, replace_text)
            dpg.set_value(tag, new_value)
        dpg.delete_item("replace_popup")

    def load_AOIs(self, xml_root):
        res = {}
        AOI_elements = xml_root.iter("AddOnInstructionDefinition")
        for elem in AOI_elements:
            AOI_name = elem.attrib.get("Name")
            AOI_rev = elem.attrib.get("Revision")
            for param in elem.find("Parameters"):
                if param.attrib.get("Name") == "cDeviceID" and AOI_name != "MCP_Device":
                    res[AOI_name] = {"Revision": AOI_rev}
                    break
            if AOI_name in res:
                for param in elem.find("Parameters"): 
                    AOI_diag_word = param.attrib.get("Name")
                    if AOI_diag_word.lower() in DIAGNOSTIC_WORDS:
                        for comment in param.find("Comments"):
                            operand = comment.attrib.get("Operand")
                            texts = {lan: "" for lan in LANGUAGES}
                            for loc_comm in comment.findall("LocalizedComment"):
                                lan = loc_comm.attrib.get("Lang")
                                text = loc_comm.text.replace("\n", "")
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
                    texts = {lan: "" for lan in LANGUAGES}
                    for loc_comm in comment.findall("LocalizedComment"):
                        lan = loc_comm.attrib.get("Lang")
                        text = loc_comm.text.replace("\n", "")
                        texts[lan] = text             
                    res[diag] = texts
        return res  

    def update_layout(self):
        try:
            # Get total viewport width
            viewport_width = dpg.get_viewport_width()
            # Calculate remaining space for center
            center_width = viewport_width - dpg.get_item_width("left_panel") - dpg.get_item_width("right_panel") - 40
            center_width = max(center_width, 100)
            dpg.set_item_width("center_panel", center_width)
        except Exception as e:
            pass

    def resize_left(self, sender, app_data, user_data):
        new_width = max(80, 200 + app_data)
        dpg.set_item_width("left_panel", new_width)
        self.update_layout()

    def resize_right(self, sender, app_data, user_data):
        new_width = max(80, 200 - app_data)
        dpg.set_item_width("right_panel", new_width)
        self.update_layout()

    def load_callback(self, sender, file_data):
        file_path = file_data['file_path_name']
        try:
            self.clear()
            parser = etree.XMLParser(strip_cdata=False)
            self.tree = etree.parse(file_path, parser)
            xml_root = self.tree.getroot()
            self.AOIs = self.load_AOIs(xml_root)
            self.instances = self.load_instances(xml_root)
            dpg.delete_item(self._window, children_only=True)
            self.create_main_menu()
            self.create_layout()
            # Pre-load diagnostics
            # Display corresponding diagnostics and remember selection
            for ins_name in self.instances.keys():
                self.display_diagnostics(ins_name, False)
        except Exception as e:
            print("Error loading file:", e)
            return
    
    def create_main_menu(self):
        with dpg.menu_bar(parent=self._window):
            with dpg.menu(label="Main"):
                dpg.add_menu_item(label="Load", callback=self.select_load_file)
                dpg.add_menu_item(label="Save", callback=self.select_save_file)
                dpg.add_separator()
                dpg.add_menu_item(label="Exit", callback=self.exit_app)
            with dpg.menu(label="Tools"):
                dpg.add_menu_item(label="Fix all", callback=self.fix_all_diagnostics)
            with dpg.menu(label="Help"):
                dpg.add_menu_item(label="Help")
                dpg.add_separator()
                dpg.add_menu_item(label="About", callback=self.test)

    def create_layout(self):
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
                with dpg.group(horizontal=True, tag="button_group"):
                    dpg.add_button(label="Fix", callback=self.fix_diagnostics, tag="fix_button")
                    dpg.add_button(label="Edit", callback=self.edit_diagnostics, tag="edit_button")
                    dpg.add_button(label="Save", callback=self.save_edits, tag="save_button", show=False)
                    dpg.add_button(label="Cancel", callback=self.cancel_edits, tag="cancel_button", show=False)
                    dpg.add_button(label="Copy Table", callback=self.copy_table, tag="copy_table_button", show=False)
                    dpg.add_button(label="Copy Column", callback=self.copy_column, tag="copy_button", show=False)
                    dpg.add_button(label="Paste Column", callback=self.paste_column, tag="paste_button", show=False)
                    dpg.add_button(label="Replace", callback=self.show_replace_popup, tag="replace_button", show=False)
                # Scrollable area for the table
                with dpg.child_window(tag="table_scroll_area", height=-1, border=False):
                    with dpg.table(tag="diag_table", header_row=True, resizable=True, borders_innerH=True, borders_innerV=True, policy=dpg.mvTable_SizingStretchProp, freeze_rows=1):
                        dpg.add_table_column(label="Diagnostic")
                        dpg.add_table_column(label="Language")
                        dpg.add_table_column(label="Instance Description")
                        dpg.add_table_column(label="AOI Description")
            # SPLITTER BAR 2
            dpg.add_drag_float(label="", width=10, default_value=0, min_value=-500, max_value=500, callback=self.resize_right)
            # AOI PANEL
            with dpg.child_window(tag="right_panel", width=200, border=True):
                with dpg.tree_node(label="AOIs", default_open=True):
                    for aoi in self.AOIs.keys():
                        dpg.add_text(f"{aoi} (v{self.AOIs[aoi]['Revision']})") 
        self.update_layout()

    def run(self):
        dpg.create_context()
        # WINDOW
        self._window = dpg.add_window(tag="Primary Window", label="Example Window")
        # MAIN MENU
        self.create_main_menu()
        # VIEWPORT
        dpg.create_viewport(title=f'MCP Diagnostics Tool - v{VERSION}', width=800, height=640)
        dpg.setup_dearpygui()
        dpg.show_viewport()
        dpg.set_viewport_resize_callback(self.update_layout)
        dpg.set_primary_window("Primary Window", True)
        # below replaces, start_dearpygui()
        while dpg.is_dearpygui_running() and self._keep_alive:
            # insert here any code you would like to run in the render loop
            # you can manually stop by using stop_dearpygui()
            dpg.render_dearpygui_frame()
        dpg.destroy_context()
        
    def save_callback(self, sender, file_data):
        file_path = file_data['file_path_name']
        try:
            self.tree.write(file_path, encoding="utf-8", xml_declaration=True)
        except Exception as e:
            print("Error saving file:", e)
            return

    def fix_diagnostics(self, sender):
        """Refresh diagnostics for the currently selected instance."""
        # AOI Diagnostics
        diag_aoi = self.AOIs[self.instances[self.current_instance]["datatype"]]
        diag_aoi.pop("Revision", None)
        # Local Diagnostics in XML
        xml_node = self.instances[self.current_instance]["XML_node"]
        # Create comments node if not existing
        comments = xml_node.find("Comments")
        if comments is None:
            comments = etree.SubElement(xml_node, "Comments")
        # Copy AOI diagnostics to instance
        for diag, texts_aoi in diag_aoi.items():
            for comment in comments.findall("Comment"):
                # Diag exists
                if comment.attrib.get("Operand").lower()[1:] == diag:
                    # Remove not allowed languages
                    for loc in comment.findall("LocalizedComment"):
                        if loc.attrib.get("Lang") not in LANGUAGES:
                            comment.remove(loc)
                    # Allowed language, check if needs update
                    for lan, text_aoi in texts_aoi.items():
                        for loc in comment.findall("LocalizedComment"):
                            if loc.attrib.get("Lang") == lan:
                                # Overwrite not allowed diagnostic text only
                                if text_aoi in ["DO NOT USE", "ANVÄND EJ"] or text_aoi[:2] not in DIAG_TYPES or loc.text == "":
                                    loc.text = etree.CDATA(text_aoi)
                                break
                        else:
                            # Language missing, create it
                            etree.SubElement(comment, "LocalizedComment", {"Lang": lan}).text = etree.CDATA(text_aoi)
                    break
            else:
                # Diag does not exist, create it
                comment = etree.SubElement(comments, "Comment", {"Operand": f".{diag}"})
                for lan, text_aoi in texts_aoi.items():
                    etree.SubElement(comment, "LocalizedComment", {"Lang": lan}).text = etree.CDATA(text_aoi)    
        # Refresh displayed diagnostics
        self.display_diagnostics(self.current_instance)

    def fix_all_diagnostics(self, sender):
        """Fix diagnostics for all instances."""
        for ins_name, status in self.instance_status.items():
            if status == STATUS_OK:
                self.current_instance = ins_name
                self.fix_diagnostics(None)

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

