import argparse
import cv2 as cv
import json
import os


"""
{
    image_name = "image.jpg",
    image_path = "/absolute/path/to/image.jpg",
    crops = [
        {
            label = "haricot",
            box = {
                x_min = 1,
                y_min = 2,
                x_max = 3,
                y_max = 4
            },
            parts = [
                {
                    kind = "stem",
                    location = {
                        x = 1,
                        y = 2
                    },

                },
                {
                    kind = "leaf",
                    location = {
                        x = 3,
                        y = 3
                    }
                }
            ]
        },
        ...
    ]
}
"""

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


class AnnotationStore:
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

    def reset(self):
        self.annotations = []

    def save_json(self, image_path, save_dir):
        if self.is_empty:
            return

        image_name = os.path.basename(image_path)
        json_repr = {
            "image_name": image_name,
            "image_path": image_path,
            "crops": [c.json_repr() for c in self.annotations]}

        save_name = os.path.join(save_dir, os.path.splitext(image_name)[0]) + ".json"

        data = json.dumps(json_repr, indent=2)
        with open(save_name, "w") as f: f.write(data)

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

    assert len(args.labels) < 10, "Can't define more than 9 labels because there are only 9 numbers in the decimal system used on keyboards and I did not count 0 to a be a number so the maximum is 9, not 10."

    if args.save_dir is None:
        args.save_dir = args.directory

    assert os.path.isdir(args.save_dir), "The save diretory you specified does not exists."

    return args


def main():
    args = parse_args()

    input_dir = args.directory
    save_dir = args.save_dir
    labels = args.labels

    images = images_in(folder=input_dir)
    image_index = 0
    image = cv.imread(images[image_index])  # Need to make this optional in case foder w/out image
    label = labels[0]

    cv.namedWindow("window", cv.WINDOW_NORMAL)
    cv.resizeWindow("window", 1200, 800)
    need_rerendering = RefCell(True)

    store = AnnotationStore()
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

    cv.setMouseCallback("window", on_mouse_event)

    while True:
        if need_rerendering.value:
            draw_img = canvas.render()
            cv.imshow("window", draw_img)
            need_rerendering.value = False

        key = cv.waitKey(15) & 0xFF
        if key == ord("q"):  # Add a save annotation here or at the end of loop
            break
        elif key == ord("z"):
            need_rerendering.value = True
            if not store.is_empty:
                last = store.annotations[-1]

                if not last.is_empty:
                    if last.box is not None:
                        last.box = None
                    else:
                        last.points.pop()
                else:
                    store.annotations.pop()
        elif key == ord("a"):
            need_rerendering.value = True
            if not store.is_empty and not store.last.is_empty:
                store.annotations.append(PlantAnnotation(label))
        elif key in [ord(f"{n}") for n in range(1, 10)]:
            need_rerendering.value = True
            index = int(chr(key))
            if index < len(labels):
                label = labels[index - 1]
        elif key == ord("e"):
            # Add a read json with a load as json
            if image_index > 0:
                store.save_json(images[image_index], save_dir)
                store.reset()
                image_index -= 1
                canvas.image = cv.imread(images[image_index])
                need_rerendering.value = True

        elif key == ord("r"):
            if image_index < len(images):
                store.save_json(images[image_index], save_dir)
                store.reset()
                image_index += 1
                canvas.image = cv.imread(images[image_index])
                need_rerendering.value = True

    cv.destroyAllWindows()


if __name__ == "__main__":
    main()
