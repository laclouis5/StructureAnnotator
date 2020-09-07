import argparse
import cv2 as cv
import json
import logging
import os


class PointAnnotation:
    def __init__(self, kind, x, y):
        self.kind = kind
        self.x = x
        self.y = y

    def draw_on(self, image):
        color = (0, 255, 0) if self.kind == "stem" else (0, 0, 255)
        cv.circle(image, center=(self.x, self.y), radius=8, color=color, thickness=-1)

    def json_repr(self):
        return {"kind": self.kind, "location": {"x": self.x, "y": self.y}}

    @classmethod
    def from_json(cls, json_dict):
        location = json_dict["location"]

        return PointAnnotation(
            json_dict["kind"],
            location["x"],
            location["y"])


class BoxAnnotation:
    def __init__(self, x=0, y=0, x2=0, y2=0):
        self.x = x
        self.y = y
        self.x2 = x2
        self.y2 = y2

    def update_tail(self, x, y):
        self.x2 = x
        self.y2 = y

    def draw_on(self, image):
        cv.rectangle(image, pt1=(self.x, self.y), pt2=(self.x2, self.y2),
            color=(255, 0, 0),
            thickness=2)

    def json_repr(self):
        return {"x_min": self.x, "y_min": self.y, "x_max": self.x2, "y_max": self.y2}

    @classmethod
    def from_json(cls, json_dict):
        return None if json_dict is None else BoxAnnotation(
            json_dict["x_min"], json_dict["y_min"],
            json_file["x_max"], json_dict["y_max"]
        )


class PlantAnnotation:
    def __init__(self, label, box=None, points=None):
        self.label = label
        self.box = None

        if points is None:
            self.points = []
        else:
            self.points = points

    def append_point(self, x, y):
        kind = "stem" if self.is_empty else "leaf"
        self.points.append(PointAnnotation(kind, x, y))
        logging.info(f"New keypoint annotation added to crop annotation (kind: {kind}, position: (x: {x}, y: {y}))")

    def draw_on(self, image):
        if self.box is not None:
            self.box.draw_on(image)

        if len(self.points) > 1:
            stem = self.points[0]
            for p in self.points[1:]:
                cv.line(image, (p.x, p.y), (stem.x, stem.y), color=(0, 0, 255), thickness=2)

        for point in self.points:
            point.draw_on(image)

    @property
    def is_empty(self):
        return len(self.points) == 0 and self.box is None

    def json_repr(self):
        box = self.box.json_repr() if self.box is not None else None
        return {"label": self.label, "box": box, "parts": [p.json_repr() for p in self.points]}

    @classmethod
    def from_json(cls, json_dict):
        return PlantAnnotation(
            json_dict["label"],
            BoxAnnotation.from_json(json_dict["box"]),
            [PointAnnotation.from_json(part) for part in json_dict["parts"]])


class ImageAnnotation:  # Change name to "ImageAnnotation"
    def __init__(self, annotations=None):
        if annotations is None:
            self.annotations = []
        else:
            self.annotations = annotations

    @property
    def last(self):
        return self.annotations[-1]

    def draw_on(self, image):
        for shape in self.annotations:
            shape.draw_on(image)

    def __len__(self):
        return len(self.annotations)

    @property
    def is_empty(self):
        return len(self) == 0

    def create_annotation_if_needed(self, label):
        if self.is_empty:
            self.annotations.append(PlantAnnotation(label))
            logging.info(f"New crop annotation added to the store (label: {label}, cause: empty store)")

    def reset(self):
        self.annotations = []

    def load_from_json(self, json_file):
        if not os.path.isfile(json_file):
            self.reset()
            return self

        with open(json_file, "r") as f: data = json.loads(f.read())
        self.annotations = [PlantAnnotation.from_json(crop) for crop in data["crops"]]
        return self

    def save_json(self, image_path, save_dir):
        image_name = os.path.basename(image_path)
        save_name = os.path.join(save_dir, os.path.splitext(image_name)[0]) + ".json"

        if self.is_empty or self.annotations[0].is_empty:
            if os.path.isfile(save_name):
                os.remove(save_name)
                logging.info("Json file `save_name` removed because it was empty")
            return

        json_repr = {
            "image_name": image_name,
            "image_path": image_path,
            "crops": [c.json_repr() for c in self.annotations if not c.is_empty]}

        data = json.dumps(json_repr, indent=2)
        with open(save_name, "w") as f: f.write(data)

        logging.info(f"Json file '{save_name}' saved")

    @classmethod
    def from_json(cls, json_file):
        with open(json_file, "r") as f: data = json.loads(f.read())
        return ImageAnnotation([PlantAnnotation.from_json(crop) for crop in data["crops"]])


class TargetCursor:
    def __init__(self, x=0, y=0):
        self.x = x
        self.y = y

    def update(self, x, y):
        self.x = x
        self.y = y

    def draw_on(self, image):
        (h, w) = image.shape[:2]

        cv.line(image, pt1=(0, self.y), pt2=(w, self.y), color=(255, 255, 255), thickness=2)
        cv.line(image, pt1=(self.x, 0), pt2=(self.x, h), color=(255, 255, 255), thickness=2)


class DragGesture:
    def __init__(self):
        self.is_dragging = False

    def __str__(self):
        return f"{self.is_dragging}"


class Canvas:
    def __init__(self, image, drawables=None):
        self.image = image
        if drawables is None:
            self.drawables = []
        else:
            self.drawables = drawables

    def render(self):
        draw_img = self.image.copy()

        for d in self.drawables:
            d.draw_on(draw_img)

        return draw_img


class RefCell:
    def __init__(self, value):
        self.value = value


def images_in(folder):
    image_extensions = [".jpg", ".jpeg", ".png"]

    files = [os.path.join(folder, file)
        for file in os.listdir(folder)
        if os.path.splitext(file)[1] in image_extensions]

    return files


def create_dir(directory):
    if not os.path.isdir(directory):
        os.mkdir(directory)


def json_name_for(image, save_dir):
    basename = os.path.basename(image)
    return os.path.join(save_dir, os.path.splitext(basename)[0]) + ".json"

def parse_args():
    parser = argparse.ArgumentParser(
        description="Annotation software for structure annotation of crops.")
    parser.add_argument("directory", help="Directory where images are stored.")
    parser.add_argument("--save_dir", "-s", default=None,
        help="Save directory for annotations. Default is the same as input directory.")
    parser.add_argument("--labels", "-l", nargs="+", default=["unknown"],
        help="Labels for crop elements. Can be accessed with 1-9 keys. Maximum is 9.")

    args = parser.parse_args()

    assert os.path.isdir(args.directory), "The input diretory you specified does not exists."
    assert len(images_in(args.directory)) > 0, "No image found in input directory. Supported images types: .jpg, .png."

    assert len(args.labels) < 10, "Can't define more than 9 labels because there are only 9 numbers in the decimal system used on keyboards and I did not count 0 to a be a number so the maximum is 9, not 10."

    if args.save_dir is None:
        args.save_dir = args.directory

    return args


def main():
    logging.basicConfig(
        filename="logs.log",
        level=logging.DEBUG,
        filemode="w",
        format="%(asctime)s %(message)s")
    args = parse_args()

    input_dir = args.directory
    save_dir = args.save_dir
    labels = args.labels

    create_dir(save_dir)

    image_index = 0
    images = sorted(images_in(folder=input_dir))
    image = cv.imread(images[image_index])
    label = labels[0]

    cv.namedWindow("Crop Structure Annotator Tool", cv.WINDOW_NORMAL)
    cv.resizeWindow("Crop Structure Annotator Tool", 1200, 800)
    need_rerendering = RefCell(True)

    store = ImageAnnotation().load_from_json(json_name_for(images[image_index], save_dir))
    cursor = TargetCursor()
    canvas = Canvas(image, [store, cursor])
    drag = DragGesture()

    def on_mouse_event(event, x, y, flags, params):
        need_rerendering.value = True
        if event == cv.EVENT_LBUTTONDBLCLK:
            drag.is_dragging = False
            store.create_annotation_if_needed(label)
            store.last.append_point(x, y)
        elif event == cv.EVENT_MOUSEMOVE:
            cursor.update(x, y)
            if drag.is_dragging:
                store.last.box.update_tail(x, y)
        elif event == cv.EVENT_MBUTTONDOWN:
            drag.is_dragging = True
            store.create_annotation_if_needed(label)
            store.last.box = BoxAnnotation(x, y, x, y)
        elif event == cv.EVENT_MBUTTONUP:
            drag.is_dragging = False
            store.last.box.update_tail(x, y)
            box = store.last.box
            logging.info(f"Bounding box added to last crop annotation (x_min: {box.x}, y_min: {box.y}, x_max: {box.x2}, y_max: {box.y2})")

    cv.setMouseCallback("Crop Structure Annotator Tool", on_mouse_event)

    while True:
        if need_rerendering.value:
            draw_img = canvas.render()
            cv.imshow("Crop Structure Annotator Tool", draw_img)
            need_rerendering.value = False

        key = cv.waitKey(15) & 0xFF
        if key == ord("q"):  # Add a save annotation here or at the end of loop
            store.save_json(images[image_index], save_dir)
            logging.info("Quiting application (cause: key 'q' pressed)")
            break
        elif key == ord("z"):
            if not store.is_empty:
                need_rerendering.value = True
                if not store.last.is_empty:
                    if store.last.box is not None:
                        store.last.box = None
                        logging.info("Last box annotation removed (cause: key 'z' pressed)")
                    else:
                        store.last.points.pop()
                        logging.info("Last keypoint annotation removed (cause: key 'z' pressed)")
                else:
                    store.annotations.pop()
                    logging.info("Last Crop annotation removed (cause: key 'z' pressed)")
            else:
                logging.info("Key 'z' pressed but there is no annotation to remove")

        elif key == ord("a"):
            if not store.is_empty and not store.last.is_empty:
                need_rerendering.value = True  # Not usefull
                store.annotations.append(PlantAnnotation(label))
                logging.info(f"New crop annotation added to the store (label: {label}, cause: key 'a' pressed)")
            else:
                logging.info("Key 'a' pressed but no crop annotation is added, an empty annotation is already ready for use")
        elif key in [ord(f"{n}") for n in range(1, 10)]:
            index = int(chr(key))
            if index <= len(labels):
                need_rerendering.value = True
                label = labels[index - 1]
                logging.info(f"Current crop label set to {label}")
        elif key == ord("e"):
            # Add a read json with a load as json
            if image_index > 0:
                store.save_json(images[image_index], save_dir)
                image_index -= 1
                canvas.image = cv.imread(images[image_index])
                store.load_from_json(json_name_for(images[image_index], save_dir))
                need_rerendering.value = True
                logging.info(f"Moving to previous image (name: {images[image_index]})")
            else:
                logging.info("Key 'e' pressed but previous images exhausted")

        elif key == ord("r"):
            if image_index < len(images):
                store.save_json(images[image_index], save_dir)
                image_index += 1
                canvas.image = cv.imread(images[image_index])
                store.load_from_json(json_name_for(images[image_index], save_dir))
                need_rerendering.value = True
                logging.info(f"Moving to next image (name: {images[image_index]})")
            else:
                logging.info("Key 'r' pressed but next images exhausted")

    cv.destroyAllWindows()


if __name__ == "__main__":
    main()
