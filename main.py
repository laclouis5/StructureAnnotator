import argparse
import cv2 as cv
from functools import lru_cache
import json
import logging
import os


class PointAnnotation:
    def __init__(self, kind, x, y):
        self.kind = kind
        self.x = x
        self.y = y

    def draw_on(self, image, style={}):
        radius = style.get("radius", 2)
        color = (0, 255, 0) if self.kind == "stem" else (0, 0, 255)
        cv.circle(image, center=(self.x, self.y), radius=radius,
            color=color, thickness=-1, lineType=cv.LINE_AA)

    def json_repr(self):
        return {"kind": self.kind, "location": {"x": self.x, "y": self.y}}

    @classmethod
    def from_json(cls, json_dict):
        location = json_dict["location"]
        return PointAnnotation(json_dict["kind"], location["x"], location["y"])


class BoxAnnotation:
    def __init__(self, x=0, y=0, x2=0, y2=0):
        self.x = x
        self.y = y
        self.x2 = x2
        self.y2 = y2

    def update_tail(self, x, y):
        self.x2 = x
        self.y2 = y

    @property
    def x_min(self): return min(self.x, self.x2)

    @property
    def y_min(self): return min(self.y, self.y2)

    @property
    def x_max(self): return max(self.x, self.x2)

    @property
    def y_max(self): return max(self.y, self.y2)

    @property
    def width(self): return self.x_max - self.x_min

    @property
    def height(self): return self.y_max - self.y_min

    @property
    def x_mid(self): return int((self.x_min + self.x_max) / 2)

    @property
    def y_mid(self): return int((self.y_min + self.y_max) / 2)

    def draw_on(self, image, style={}):
        thickness = style.get("thickness", 2)
        cv.rectangle(image, pt1=(self.x_min, self.y_min), pt2=(self.x_max, self.y_max),
            color=(255, 0, 0), thickness=thickness, lineType=cv.LINE_AA)

    def json_repr(self):
        return {
            "x_min": self.x_min, "y_min": self.y_min,
            "x_max": self.x_max, "y_max": self.y_max}

    @classmethod
    def from_json(cls, json_dict):
        if not json_dict: return None

        return BoxAnnotation(
            json_dict["x_min"], json_dict["y_min"],
            json_dict["x_max"], json_dict["y_max"])


class PlantAnnotation:
    def __init__(self, label, box=None, points=None):
        self.label = label
        self.box = box
        self.points = points if points else []

    def append_point(self, x, y):
        kind = "stem" if not self.points else "leaf"
        self.points.append(PointAnnotation(kind, x, y))
        logging.info(f"New keypoint annotation added (kind: {kind}, position: (x: {x}, y: {y}))")

    def draw_on(self, image, style={}):
        thickness = style.get("thickness", 2)
        radius = style.get("radius", 8)
        font_scale = style.get("font_scale", 0.33)
        font_face = style.get("font_face", cv.FONT_HERSHEY_DUPLEX)
        offset = int(1/100 * min(image.shape[:2]))

        if self.points:
            stem = self.points[0]

            for p in self.points[1:]:
                cv.line(image, (p.x, p.y), (stem.x, stem.y),
                    color=(0, 0, 255), thickness=thickness, lineType=cv.LINE_AA)

            if self.box:
                stem = self.points[0]
                (x, y) = self.box.x_mid, self.box.y_mid
                cv.circle(image, center=(x, y), radius=radius,
                    color=(255, 0, 0), thickness=-1, lineType=cv.LINE_AA)
                cv.line(image, (x, y), (stem.x, stem.y),
                    color=(255, 0, 0), thickness=thickness, lineType=cv.LINE_AA)

        [p.draw_on(image, style) for p in self.points]

        if self.box:
            self.box.draw_on(image, style)

            if not self.points:
                cv.putText(image, self.label.upper(),
                    org=(self.box.x_min + offset, self.box.y_min - offset),
                    fontFace=font_face, fontScale=font_scale,
                    color=(255, 255, 255), thickness=thickness, lineType=cv.LINE_AA)

        if self.points:
            stem = self.points[0]
            cv.putText(image, self.label.upper(), org=(stem.x + offset, stem.y - offset),
                fontFace=font_face, fontScale=font_scale,
                color=(255, 255, 255), thickness=thickness, lineType=cv.LINE_AA)

    @property
    def is_empty(self):
        return not self.points and not self.box

    def json_repr(self):
        box = self.box.json_repr() if self.box else None
        return {"label": self.label, "box": box, "parts": [p.json_repr() for p in self.points]}

    @classmethod
    def from_json(cls, json_dict):
        return PlantAnnotation(
            json_dict["label"],
            BoxAnnotation.from_json(json_dict.get("box", None)),
            [PointAnnotation.from_json(part) for part in json_dict["parts"]])


class ImageAnnotation:
    def __init__(self, annotations=None):
        self.annotations = annotations if annotations else []
        self._target_index = len(annotations) - 1 if annotations else None

    @property
    def target_index(self):
        return self._target_index

    @target_index.setter
    def target_index(self, value):
        if len(self) != 0:
            self._target_index = value % len(self)
        else:
            self._target_index = None

    @property
    def target(self):
        return self.annotations[self.target_index]

    @property
    def last(self):
        return self.annotations[-1]

    def append(self, annotation):
        self.annotations.append(annotation)
        self.target_index = len(self.annotations) - 1

    def pop_target(self):
        if not self.annotations:
            self.target_index = None
        else:
            del self.annotations[self.target_index]
            self.target_index -= 1

    def draw_on(self, image, style={}):
        for annotation in self.annotations:
            annotation.draw_on(image, style)

        if len(self.annotations) > 0 and len(self.target.points) > 0:
            radius = int(style.get("radius", 8) * 0.5)
            cv.circle(image, (self.target.points[0].x, self.target.points[0].y),
                radius=radius, color=(255, 0, 0), thickness=-1, lineType=cv.LINE_AA)
        elif len(self.annotations) > 0 and self.target.box is not None:
            radius = int(style.get("radius", 8) * 0.5)
            offset = int(1/100 * min(image.shape[:2]))
            cv.circle(image, (self.target.box.x_min, self.target.box.y_min - offset),
                radius=radius, color=(255, 0, 0), thickness=-1, lineType=cv.LINE_AA)

    def __len__(self):
        return len(self.annotations)

    @property
    def is_empty(self):
        return len(self) == 0

    def create_annotation_if_needed(self, label):
        if self.is_empty:
            self.annotations.append(PlantAnnotation(label))
            self.target_index = 0
            logging.info(f"New crop annotation with label '{label}' added (cause: no current crop annotation)")

    def reset(self):
        self.annotations = []
        self.target_index = None

    def load_from_json(self, json_file):
        if not os.path.isfile(json_file):
            self.reset()
            return self

        with open(json_file, "r") as f: data = json.loads(f.read())
        self.annotations = [PlantAnnotation.from_json(crop) for crop in data["crops"]]
        self.target_index = len(self.annotations) - 1
        logging.info(f"Annotations loaded from json file '{json_file}'")

        return self

    def save_json(self, image_path, save_dir):
        image_name = os.path.basename(image_path)
        save_name = os.path.join(save_dir, os.path.splitext(image_name)[0]) + ".json"

        if self.is_empty or self.annotations[0].is_empty:  # Hacky thing...?
            if os.path.isfile(save_name):
                os.remove(save_name)
                logging.info(f"Json file {save_name} removed because it was empty")
            return

        json_repr = {
            "image_name": image_name,
            "image_path": image_path,
            "crops": [c.json_repr() for c in self.annotations if not c.is_empty]}

        data = json.dumps(json_repr, indent=2)
        with open(save_name, "w") as f: f.write(data)

        logging.info(f"Saved Json file '{save_name}'")

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

    def draw_on(self, image, style={}):
        thickness = style.get("thickness", 2)
        (h, w) = image.shape[:2]

        cv.line(image, pt1=(0, self.y), pt2=(w, self.y),
            color=(255, 255, 255), thickness=thickness, lineType=cv.LINE_AA)
        cv.line(image, pt1=(self.x, 0), pt2=(self.x, h),
            color=(255, 255, 255), thickness=thickness, lineType=cv.LINE_AA)


class LabelView:
    def __init__(self, label):
        self.label = label

    def draw_on(self, image, style={}):
        thickness = style.get("thickness", 2)
        font_scale = style.get("font_scale", 0.33) * 1.25
        font_face = style.get("font_face", cv.FONT_HERSHEY_DUPLEX)
        offset = int(1/100 * min(image.shape[:2]))

        cv.putText(image, "Current crop label: " + self.label.upper(),
            org=(0 + offset, image.shape[0] - offset),
            fontFace=font_face, fontScale=font_scale, color=(255, 255, 255),
            thickness=thickness, lineType=cv.LINE_AA)


class Canvas:
    def __init__(self, image, drawables=None):
        self.image = image
        self.drawables = drawables if drawables else []

    def render(self):
        draw_img = self.image.copy()
        (img_h, img_w) = draw_img.shape[:2]
        short_side = min(img_h, img_w)
        style = {
            "radius": int(0.75/100 * short_side),
            "thickness": int(0.3/100 * short_side),
            "font_scale": 0.05/100 * short_side}

        [d.draw_on(draw_img, style) for d in self.drawables]

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


class ImageReader:
    def __init__(self, image_folder):
        self.folder = image_folder
        self.images = sorted(images_in(image_folder))
        self._index = 0

        assert len(self.images) > 0, "No images"

    @property
    def index(self):
        return self._index

    @index.setter
    def index(self, value):
        self._index = min(max(value, 0), len(self) - 1)

    def next(self):
        self.index += 1
        return self.img

    def prev(self):
        self.index -= 1
        return self.img

    @property
    def img(self):
        return self._img_for_index(self.index)

    @lru_cache(maxsize=32)
    def _img_for_index(self, index):
        return cv.imread(self.images[index])

    @property
    def img_name(self):
        return self.images[self.index]

    def __len__(self):
        return len(self.images)


def create_dir_if_needed(directory):
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

    assert len(args.labels) < 10, "Can't define more than 9 labels because there are only 9 numbers in the decimal system used on keyboards and I did not count 0 to a be a number so the maximum is 9, not 10. Maybe I'll add two keys for changing labels (- and +) so this limits will no longer holds in the future."

    if not args.save_dir: args.save_dir = args.directory
    create_dir_if_needed(args.save_dir)

    return args


def main():
    logging.basicConfig(
        filename="logs.log", level=logging.DEBUG,
        filemode="w", format="%(asctime)s %(message)s")
    logging.info("Application started")

    args = parse_args()
    input_dir = args.directory
    save_dir = args.save_dir
    labels = args.labels

    label = labels[0]  # `labels` is never empty
    img_reader = ImageReader(input_dir)

    cv.namedWindow("Crop Structure Annotation Tool", cv.WINDOW_NORMAL)
    cv.resizeWindow("Crop Structure Annotation Tool", 800, 800)
    need_rerendering = RefCell(True)

    store = ImageAnnotation().load_from_json(json_name_for(img_reader.img_name, save_dir))
    cursor = TargetCursor()
    label_view = LabelView(label)
    canvas = Canvas(img_reader.img, [store, cursor, label_view])

    def on_mouse_event(event, x, y, flags, params):
        if event == cv.EVENT_LBUTTONDBLCLK:
            need_rerendering.value = True
            store.create_annotation_if_needed(label)
            store.target.append_point(x, y)
        elif event == cv.EVENT_MOUSEMOVE:
            need_rerendering.value = True
            cursor.update(x, y)
            if flags == (cv.EVENT_FLAG_LBUTTON + cv.EVENT_FLAG_SHIFTKEY):
                store.target.box.update_tail(x, y)
        elif flags == (cv.EVENT_FLAG_LBUTTON + cv.EVENT_FLAG_SHIFTKEY) \
            and event == cv.EVENT_LBUTTONDOWN:
            need_rerendering.value = True
            store.create_annotation_if_needed(label)
            store.target.box = BoxAnnotation(x, y, x, y)
        elif flags == (cv.EVENT_FLAG_LBUTTON + cv.EVENT_FLAG_SHIFTKEY) \
            and event == cv.EVENT_LBUTTONUP:
            need_rerendering.value = True
            store.target.box.update_tail(x, y)
            box = store.target.box
            logging.info(f"Bounding box added to target crop annotation (x_min: {box.x_min}, y_min: {box.y_min}, x_max: {box.x_max}, y_max: {box.y_max})")

    cv.setMouseCallback("Crop Structure Annotation Tool", on_mouse_event)

    while True:
        if need_rerendering.value:
            draw_img = canvas.render()
            cv.imshow("Crop Structure Annotation Tool", draw_img)
            need_rerendering.value = False

        key = cv.waitKey(15) & 0xFF
        if key == ord("q"):
            store.save_json(img_reader.img_name, save_dir)
            logging.info("Quiting application (cause: key 'q' pressed)")
            break
        elif key == ord("z"):
            if not store.is_empty:
                need_rerendering.value = True
                if not store.target.is_empty:
                    if store.target.box:
                        store.target.box = None
                        logging.info("Last box annotation removed (key 'z' pressed)")
                    else:
                        store.target.points.pop()
                        logging.info("Last keypoint annotation removed (key 'z' pressed)")
                else:
                    store.pop_target()
                    logging.info("Last Crop annotation removed (key 'z' pressed)")
            else:
                logging.info("Key 'z' pressed but there is no annotation to remove")
        elif key == ord("a"):
            need_rerendering.value = True
            if not store.is_empty and not store.last.is_empty:
                store.append(PlantAnnotation(label))
                logging.info(f"New crop annotation with label '{label}' added (key 'a' pressed)")
            else:
                store.target_index = len(store.annotations) - 1
                logging.info("Key 'a' pressed but no crop annotation added, an empty annotation is already in use")
        elif key in [ord(f"{n}") for n in range(1, 10)]:
            index = int(chr(key))
            if index <= len(labels):
                need_rerendering.value = True
                label = labels[index - 1]
                label_view.label = label
                if not store.is_empty:
                    store.target.label = label
                logging.info(f"Current crop label set to {label}")
        elif key == ord("e"):
            if img_reader.index > 0:
                store.save_json(img_reader.img_name, save_dir)
                canvas.image = img_reader.prev()
                logging.info(f"Moved to previous image '{img_reader.img_name}'")
                store.load_from_json(json_name_for(img_reader.img_name, save_dir))
                need_rerendering.value = True
        elif key == ord("r"):
            if img_reader.index < len(img_reader) - 1:
                store.save_json(img_reader.img_name, save_dir)
                canvas.image = img_reader.next()
                logging.info(f"Moved to next image '{img_reader.img_name}'")
                store.load_from_json(json_name_for(img_reader.img_name, save_dir))
                need_rerendering.value = True
        elif key == ord("s"):
                store.save_json(img_reader.img_name, save_dir)
        elif key == ord("w"):
            store.target_index -= 1
            logging.info("Targeted crop changed to previous one")
            need_rerendering.value = True
        elif key == ord("x"):
            store.target_index += 1
            logging.info("Targeted crop changed to next one")
            need_rerendering.value = True

    cv.destroyAllWindows()
    logging.info("Application ended")


if __name__ == "__main__":
    main()
