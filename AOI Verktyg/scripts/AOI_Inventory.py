from helpers import execute_function
import pandas as pd

def AOI_Inventory_Versions(filename, xml_root):
    results = []
    for elem in xml_root.iter("AddOnInstructionDefinition"):
        aoi_name = elem.attrib.get("Name")
        if aoi_name[0] != "_":
            results.append({
                "Area": ("_").join(filename.split("_")[1:3]),
                "PLC": filename.split("_")[3],
                "AOI": aoi_name,
                "Revision": elem.attrib.get("Revision"),
            })
    return results

def AOI_Inventory_Instances(filename, xml_root):
    AOI_names = []
    AOI_elements = xml_root.iter("AddOnInstructionDefinition")
    for elem in AOI_elements:
        if elem.attrib.get("Name")[0] != "_":
            AOI_names.append(elem.attrib.get("Name"))
    results = []
    for tag in xml_root.find("Controller").find("Tags"):
        if tag.attrib.get("DataType") in AOI_names:
            results.append({
                "Area": ("_").join(filename.split("_")[1:3]),
                "PLC": filename.split("_")[3],
                "Scope": "Controller",
                "AOI": tag.attrib.get("DataType"),
                "Name": tag.attrib.get("Name")
            })
    for program in xml_root.find("Controller").find("Programs").findall("Program"):
        for tag in program.find("Tags"):
            if tag.attrib.get("DataType") in AOI_names:
                results.append({
                    "PLC": filename,
                    "Scope": program.attrib.get("Name"),
                    "AOI": tag.attrib.get("DataType"),
                    "Name": tag.attrib.get("Name")
                })
    return results

def Inventory_analyze():
    df = pd.read_csv("AOI_Inventory_Instances.csv")
    grouped = df.groupby(["PLC", "AOI"]).size().reset_index(name="COUNT")
    grouped.to_csv("AOI_Inventory_Instance_Totals.csv", index=False)

def Versions_analyze():
    df = pd.read_csv("AOI_Inventory_Versions.csv")
    grouped = df.groupby(["Area","Revision", "AOI"]).agg({"PLC":list}).reset_index()
    grouped.to_csv("AOI_Inventory_Versions_Totals.csv", index=False)

def Alarm_list(filename, xml_root):
    DIAGNOSTIC_WORDS = ["idiagnostic1", "idiagnostic2", "idiagnostic3", "idiagnostic4", "idiagnostic5"]

    area = ("_").join(filename.split("_")[1:3])
    plc = filename.split("_")[3]

    AOIs_with_diagnostics = {}
    AOI_elements = xml_root.iter("AddOnInstructionDefinition")
    for elem in AOI_elements:
        for param in elem.find("Parameters"):
            if "iDiagnostic" in param.attrib.get("Name"):
                AOIs_with_diagnostics[elem.attrib.get("Name")] = elem
    results = []

    for tag in xml_root.find("Controller").find("Tags").findall("Tag"):
        datatype = tag.attrib.get("DataType")
        if datatype in AOIs_with_diagnostics:
            tag_name = tag.attrib.get("Name")
            # AOI global alarms
            elem = AOIs_with_diagnostics[datatype]
            for param in elem.find("Parameters"):
                param_name = param.attrib.get("Name")
                if param_name.lower() in DIAGNOSTIC_WORDS:
                    for comment in param.find("Comments"):
                        res = {
                            "Area": area,
                            "PLC": plc,
                            "Tag": tag_name,
                            "DaraType": datatype,
                            "Diagnostic": param_name,
                            "Bit": comment.attrib.get("Operand")[1:],
                            "User_defined":False,
                            "en-GB":"",
                            "sv-SE":"",
                            "xx-XX":"",
                        }
                        for loc_comm in comment.findall("LocalizedComment"):
                            lan = loc_comm.attrib.get("Lang")
                            text = loc_comm.text.replace("\n", "")
                            if lan in ["en-GB", "sv-SE"]:
                                res[lan] = text
                            else:
                                res["xx-XX"] = lan + "-" + text
                        # Filter short texts: UF_01, W_02, etc.
                        if len(res["en-GB"])>5:
                            results.append(res)
            # Instance Alarms
            comments = tag.find("Comments")
            if comments is not None:
                for comment in comments.findall("Comment"):
                    param_name = comment.attrib.get("Operand")
                    bit = param_name.split(".")[-1]
                    param_name = param_name.split(".")[1].lower()
                    if param_name in DIAGNOSTIC_WORDS:
                        res = {
                            "Area": area,
                            "PLC": plc,
                            "Tag": tag_name,
                            "DaraType": datatype,
                            "Diagnostic": param_name,
                            "Bit": bit,
                            "User_defined":True,
                            "en-GB":"",
                            "sv-SE":"",
                            "xx-XX":"",
                        }
                        for loc_comm in comment.findall("LocalizedComment"):
                            lan = loc_comm.attrib.get("Lang")
                            text = loc_comm.text.replace("\n", "")
                            if lan in ["en-GB", "sv-SE"]:
                                res[lan] = text
                            else:
                                res["xx-XX"] = lan + "-" + text
                        # Filter short texts: UF_01, W_02, etc.
                        if len(res["en-GB"])>5:
                            results.append(res)

    return results

def Alarms_analyze():
    df = pd.read_csv("Alarm_list.csv")
    df_grouped = df.groupby(["PLC", "Area"]).size().reset_index(name="Count")
    df_sorted = df_grouped.sort_values(by="Count", ascending=False) 
    df_sorted.to_csv("Alarm_list_Totals.csv", index=False)


# Run the process
if __name__ == "__main__":
    #execute_function("AOI_Inventory_Versions.csv", AOI_Inventory_Versions)
    #Versions_analyze()
    #execute_function("AOI_Inventory_Instances.csv", AOI_Inventory_Instances)
    #Inventory_analyze()
    #execute_function("Alarm_list.csv", Alarm_list)
    Alarms_analyze()
