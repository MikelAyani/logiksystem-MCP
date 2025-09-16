import os
from lxml import etree
import csv

# Configuration
FILENAME = "_13_EXC_OP090.L5X"
DIAGNOSTIC_WORDS = ["idiagnostic1", "idiagnostic2", "idiagnostic3"]

# Crawl directory and process XML files
def copy_diags(filename):
    DIAGNOSTIC_WORDS = ["idiagnostic1", "idiagnostic2", "idiagnostic3", "idiagnostic4", "idiagnostic5"]
    try:
        parser = etree.XMLParser(strip_cdata=False)
        tree = etree.parse("./data/"+filename, parser)
        xml_root = tree.getroot()

        AOIs_with_diagnostics = {}
        AOI_elements = xml_root.iter("AddOnInstructionDefinition")
        for elem in AOI_elements:
            AOI_name = elem.attrib.get("Name")
            for param in elem.find("Parameters"):
                if param.attrib.get("Name")== "cDeviceID" and AOI_name != "MCP_Device":
                    AOIs_with_diagnostics[AOI_name] = {}
                    print("new AOI found:", elem.attrib.get("Name"))
                    break
            
            if AOI_name in AOIs_with_diagnostics:
                for param in elem.find("Parameters"): 
                    AOI_diag_word = param.attrib.get("Name")
                    if AOI_diag_word.lower() in DIAGNOSTIC_WORDS:
                        word = int(AOI_diag_word[-1])-1
                        AOIs_with_diagnostics[AOI_name][word] = {}
                        for comment in param.find("Comments"):
                            operand = comment.attrib.get("Operand")
                            bit = int(operand[1:])
                            AOIs_with_diagnostics[AOI_name][word][bit] = {}
                            for loc_comm in comment.findall("LocalizedComment"):
                                lan = loc_comm.attrib.get("Lang")
                                text = loc_comm.text.replace("\n", "")
                                if lan in ["en-GB", "sv-SE"]:
                                    AOIs_with_diagnostics[AOI_name][word][bit][lan] = text
                
        for tag in xml_root.find("Controller").find("Tags").findall("Tag"):
            datatype = tag.attrib.get("DataType")
            if datatype in AOIs_with_diagnostics:
                tag_name = tag.attrib.get("Name")
                # AOI global alarms
                AOI_Global = AOIs_with_diagnostics[datatype]

                # Instance Alarms
                checklist = [[False]*32, [False]*32, [False]*32]
                comments = tag.find("Comments")
                if comments is not None:
                    for comment in comments.findall("Comment"):
                        operand = comment.attrib.get("Operand")
                        param_name = operand[1:len("iDiagnosticX")+1].lower()
                        if len(operand)>len(".iDiagnosticX."):
                            bit = int(operand[len(".iDiagnosticX."):])
                            word = int(param_name[-1])-1
                            if param_name in DIAGNOSTIC_WORDS:
                                for loc_comm in comment.findall("LocalizedComment"):
                                    lan = loc_comm.attrib.get("Lang")
                                    text = loc_comm.text.replace("\n", "")
                                    if text != "":
                                        checklist[word][bit] = True
                                        #print(tag_name, param_name, word, bit, lan, text)
                else:
                    comments = etree.Element("Comments")
                    data_node = tag.find("Data")
                    i = tag.index(data_node)
                    tag.insert(i, comments)
                for word in range(3):
                    for bit in range(32):
                        if not checklist[word][bit]:
                            """
                            <Comment Operand=".IDIAGNOSTIC2.1">
                            <LocalizedComment Lang="en-GB">
                            <![CDATA[UF_Ilegal Variant ID from PLC]]>
                            </LocalizedComment>
                            <LocalizedComment Lang="sv-SE">
                            <![CDATA[UF_Gripare strö helt stängd (Tappat strö?)]]>
                            </LocalizedComment>
                            </Comment>
                            """
                            new_comment = etree.SubElement(comments, "Comment")
                            new_comment.set('Operand', f".IDIAGNOSTIC{word+1}.{bit}")
                            for lang in ["en-GB", "sv-SE"]:
                                loc_comment = etree.SubElement(new_comment, "LocalizedComment")
                                loc_comment.set('Lang', lang)
                                text_comment = AOI_Global[word][bit][lang]
                                loc_comment.text = etree.CDATA(text_comment)
                                #print(tag_name, param_name, word, bit, lang, text_comment)
                    
        tree.write(FILENAME,encoding="utf-8", xml_declaration=True)
    except Exception as e:
        print(f"Error parsing {filename}: {e}")

if __name__ == "__main__":
    copy_diags(FILENAME)