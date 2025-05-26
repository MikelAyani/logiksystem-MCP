import os
import xml.etree.ElementTree as ET
import csv

# Configuration
FOLDER_PATH = "./data"
FILE_EXTENSION = ".L5X"

# Crawl directory and process XML files
def process_folder(folder_path, file_extension, xml_function):
    results = []
    for root, _, files in os.walk(folder_path):
        for file in files:
            if file.lower().endswith(file_extension.lower()):
                file_path = os.path.join(root, file)
                try:
                    tree = ET.parse(file_path)
                    xml_root = tree.getroot()
                    results_file = xml_function(file.split(".")[0], xml_root)
                    results += results_file
                except ET.ParseError as e:
                    print(f"Error parsing {file_path}: {e}")
    return results

# Write results to CSV
def write_csv(data, output_path):
    if not data:
        print("No data to write.")
        return
    fieldnames = data[0].keys()
    with open(output_path, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)
    print(f"CSV written to {output_path}")

def execute_function(output_file:str, method):
    xml_data = process_folder(FOLDER_PATH, FILE_EXTENSION, method)
    write_csv(xml_data, output_file)