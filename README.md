# Structure Annotator
Software for annotating images with the structure of crops. Work still in progress and documentation is not complete, use at you own risk.

![illustration](illustration.png)

## Requirements and Installation
- Python3
- OpenCV

Installing in a virtual environment is recommended. Download and unzip this repo if needed then `cd` in the main directory and issue in a terminal window:
`pip3 install -r requirements.txt`. This will install required dependencies.

## How to Use
- `cd` in the project directory (should be `StructureAnnotator/`).
- Launch the software with `python3 main.py [ARGUMENTS...]`. Read the documentation with `python3 main.py -h` for more information on the arguments.

This software can annotate crops, which are composed of one stem (green), some leaves (red) and one optional bounding box (blue). The crop parts (stem and leaves) are represented as key-points. Here is the list of commands and actions:
- Double click (left): add a key-point to the current crop being annotated. The first one will be the stem and the others leaves.
- Left click + shift + drag gesture: add a bounding box to the current crop.
- Command `a`: creates a new crop. A new crop is automatically generated if none are present on the current image while issuing a creation command.
- Command `z`: undo the last action (if present, the bounding box is always treated as the last annotated element). Redo is not supported.
- Commands `e` and `r`: move to previous or next image. This saves the current annotation file automatically.
- Commands `w` and `x`: focus previous or next crop annotation. The focused annotation is represented by a blue circle next to the box or the stem. No visible circle means that a new empty annotation is focused.
- Commands `1` to `9`: change the crop annotation label that will be used when a new annotation is created.
- Command `s`: manually save the annotation. Not necessary since quitting the program of moving between images triggers saving.
- Command `q`: quits the program.
- Logs can be streamed in real time by opening `logs.log` in a console.

## Output Format
Annotations are saved as JSON files in the specified save directory and the filename is the same as the corresponding image with a `.json` extension.

Here is an example for image `image_1.jpg`. The annotation file `image_1.json` has exactly one crop annotation with 1 stem, 1 leaf and 1 bounding box:

```json
{
  "image_name": "image_1.jpg",
  "image_path": "/path/to/image_1.jpg",
  "crops": [
    {
      "label": "bean",
      "box": {
        "x_min": 1687,
        "y_min": 531,
        "x_max": 2070,
        "y_max": 829
      },
      "parts": [
        {
          "kind": "stem",
          "location": {
            "x": 1927,
            "y": 680
          }
        },
        {
          "kind": "leaf",
          "location": {
            "x": 1684,
            "y": 821
          }
        }
      ]
    }
  ]
}
```

## Todo
- [x] Add commands to change image
- [x] Add a command to save annotation
- [x] Add loading of annotations
- [x] Solve issue when input folder is empty
- [x] Add normalized key-point point rendering
- [x] Add label text to figure
- [x] Add indicator of which label is in use
- [x] Change current crop focus
- [ ] Parse XML files for faster annotation (separate utility tool)
- [ ] Add NN pre-annotation
- [ ] Add a command to change folder

## Will Not Do
- Clean code and refactor
- Add new functionality

## Known Issues
- Creating N (>= 2) crop annotations, changing target to n != N and removing all parts with `z` will leave a hole in the internal buffer. This bug will not create empty annotations in the output JSON file since empty-ness is checked before saving.
