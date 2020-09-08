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

This software can annotate crops, which are composed of one stem (green), some leaves (red) and one optional bounding box (blue). The crop parts (stem and leaves) are represented as keypoints. Here is the list of commands and actions:
- Double click (left): add a keypoint to the current crop being annotated. The first one will be the stem and the others leaves.
- Left click + shift + drag gesture: add a bounding box to the current crop.
- Command `a`: creates a new crop. A new crop is automatically generated if none are present on the current image while issuing a creation command.
- Command `z`: undo the last action (if present, the bounding box is always treated as the last annotated element). Redo is not supported.
- Commands `e` and `r`: move to previous or next image. This saves the current annotation file automatically.
- Commands `w` and `x`: focus previous or next crop annotation. The focused annotation is represented by a blue circle next to the box or the stem. No visible circle means that a new empty annotation is focused.
- Commands `1` to `9`: change the crop annotation label that will be used when a new annotation is created.
- Command `s`: manually save the annotation. Not necessary since quitting the program of moving between images triggers saving.
- Command `q`: quits the program.
- Logs can be streamed in real time by opening `logs.log` in a console.

## Todo
- [x] Add commands to change image
- [x] Add a command to save annotation
- [x] Add loading of annotations
- [x] Solve issue when input folder is empty
- [x] Add normalized keypoint point rendering
- [x] Add label text to figure
- [x] Add indicator of which label is in use
- [x] Change current crop focus
- [ ] Parse XML files for faster annotation (separate utility tool)
- [ ] Add NN pre-annotation
- [ ] Command to change folder

## Will Not Do
- Clean code and refactor
- Add new functionnality
