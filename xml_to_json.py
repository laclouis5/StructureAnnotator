import argparse
import json
import logging
import lxml.etree as ET
import os


def files_with_ext(folder, extension):
    return [os.path.join(folder, file)
        for file in os.listdir(folder)
        if os.path.splitext(file)[1] == extension]


def xml_to_json(input_dir, save_dir):
    xml_files = files_with_ext(input_dir, ".xml")

    for xml_file in xml_files:
        xml = ET.parse(xml_file).getroot()
        image_path = xml.find("path").text
        image_name = xml.find("filename").text
        crops = []

        for crop in xml.findall("object"):
            label = crop.find("name").text
            if "stem" not in label and "tige" not in label: continue

            box = crop.find("bndbox")
            x = int((float(box.find("xmax").text) + float(box.find("xmin").text)) / 2)
            y = int((float(box.find("ymax").text) + float(box.find("ymin").text)) / 2)

            crops.append({
                "label": label,
                "box": None,
                "parts": [{
                    "kind": "stem",
                    "location": {"x": x, "y": y}
                }]
            })

            json_dict = {"image_name": image_name, "image_path": image_path, "crops": crops}
            data = json.dumps(json_dict, indent=2)
            save_name = os.path.join(save_dir, os.path.splitext(image_name)[0] + ".json")
            with open(save_name, "w") as f: f.write(data)


def create_dir_if_needed(directory):
    if not os.path.isdir(directory):
        os.mkdir(directory)


def parse_args():
    parser = argparse.ArgumentParser(description="Private tool for converting XML to JSON annotations.")
    parser.add_argument("input_dir", help="The input directory where XML files are stored.")
    parser.add_argument("--save_dir", "-s", default=None, help="the directory where to store the converted files. Default is the save as input diretory. If the folder does not exist it will be created.")

    args = parser.parse_args()

    assert os.path.isdir(args.input_dir), "Input directory is not a valid directory"
    if args.save_dir is None:
        args.save_dir = args.input_dir

    create_dir_if_needed(args.save_dir)

    return args


def main():
    args = parse_args()
    xml_to_json(args.input_dir, args.save_dir)


if __name__ == "__main__":
    main()
