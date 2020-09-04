import cv2 as cv
import json

class PointAnnotation:

    def __init__(self, label, x, y):
        self.label = label
        self.x = x
        self.y = y

    def draw_on(self, image, color=(0, 0, 255)):
        cv.circle(image, center=(self.x, self.y), radius=8, color=color, thickness=-1)


class BoxAnnotation:

    def __init__(self, x=0, y=0, x2=0, y2=0):
        self.x = x
        self.y = y
        self.x2 = x2
        self.y2 = y2

    def draw_on(self, image):
        cv.rectangle(image, pt1=(self.x, self.y), pt2=(self.x2, self.y2),
            color=(255, 0, 0),
            thickness=2)


class PlantAnnotation:

    def __init__(self, box=None, points=None):
        self.box = None

        if points is None:
            self.points = []
        else:
            self.points = points

    def draw_on(self, image):
        if self.box is not None:
            self.box.draw_on(image)

        if len(self.points) != 0:
            stem = self.points[0]

            for annotation in self.points[1:]:
                annotation.draw_on(image)
                cv.line(image,
                    pt1=(annotation.x, annotation.y),
                    pt2=(stem.x, stem.y),
                    color=(0, 0, 255), thickness=2)

            stem.draw_on(image, color=(0, 255, 0))

    @property
    def is_empty(self):
        return len(self.points) == 0 and self.box is None


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


class AnnotationStore:

    def __init__(self, annotations=None):
        if annotations is None:
            self.annotations = []
        else:
            self.annotations = annotations

    def draw_on(self, image):
        for shape in self.annotations:
            shape.draw_on(image)

    def __len__(self):
        return len(self.annotations)

    @property
    def is_empty(self):
        return len(self) == 0

    def create_annotation_if_needed(self):
        if self.is_empty:
            self.annotations.append(PlantAnnotation())


class DragGesture:

    def __init__(self):
        self.is_dragging = False

    def __str__(self):
        return f"{self.is_dragging}"


def main():
    flags = cv.WINDOW_NORMAL
    cv.namedWindow("window", flags)
    cv.resizeWindow("window", 1200, 800)

    img = cv.imread("test.jpg")
    store = AnnotationStore()
    cursor = TargetCursor()
    drag = DragGesture()

    def on_mouse_event(event, x, y, flags, params):
        if event == cv.EVENT_LBUTTONDBLCLK:
            drag.is_dragging = False
            store.create_annotation_if_needed()
            store.annotations[-1].points.append(PointAnnotation("test", x, y))
        elif event == cv.EVENT_MOUSEMOVE:
            cursor.update(x, y)
            if drag.is_dragging:
                store.annotations[-1].box.x2 = x
                store.annotations[-1].box.y2 = y
        elif event == cv.EVENT_MBUTTONDOWN:
            drag.is_dragging = True
            store.create_annotation_if_needed()
            store.annotations[-1].box = BoxAnnotation()
            store.annotations[-1].box.x = x
            store.annotations[-1].box.y = y
        elif event == cv.EVENT_MBUTTONUP:
            drag.is_dragging = False
            store.annotations[-1].box.x2 = x
            store.annotations[-1].box.y2 = y

    cv.setMouseCallback("window", on_mouse_event)

    while True:
        draw_img = img.copy()
        store.draw_on(draw_img)
        cursor.draw_on(draw_img)
        cv.imshow("window", draw_img)

        key = cv.waitKey(1) & 0xFF
        if key == ord("q"):
            break
        elif key == ord("z"):
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
            if not store.is_empty and not store.annotations[-1].is_empty:
                store.annotations.append(PlantAnnotation())

    cv.destroyAllWindows()


if __name__ == "__main__":
    main()
