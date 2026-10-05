from ultralytics import YOLO
import cv2
import numpy as np


# =========================
# CONFIG
# =========================

MODEL_PATH = "yolo26n.pt"

IMG_SIZE = 640
CONFIDENCE_THRESHOLD = 0.5

# Трапеция дороги
ROAD_TOP_Y = 0.35
ROAD_TOP_WIDTH = 0.35
ROAD_BOTTOM_WIDTH = 0.90

# Какая доля bbox должна находиться внутри зоны,
# чтобы считать зону заблокированной
ZONE_BLOCK_THRESHOLD = 0.15


# =========================
# MODEL
# =========================

model = YOLO(MODEL_PATH)


# =========================
# ROAD TRAPEZOID
# =========================

def create_road_trapezoid(width, height):

    top_y = int(height * ROAD_TOP_Y)

    top_width = int(width * ROAD_TOP_WIDTH)
    bottom_width = int(width * ROAD_BOTTOM_WIDTH)

    top_x1 = (width - top_width) // 2
    top_x2 = (width + top_width) // 2

    bottom_x1 = (width - bottom_width) // 2
    bottom_x2 = (width + bottom_width) // 2

    return np.array([
        [top_x1, top_y],
        [top_x2, top_y],
        [bottom_x2, height],
        [bottom_x1, height]
    ], dtype=np.int32)


# =========================
# ROAD ZONES
# =========================

def create_road_zones(road_polygon):

    # Трапеция:
    #       top
    #    /-------\
    #   /         \
    #  /-----------\
    # left center right

    tl = road_polygon[0]
    tr = road_polygon[1]
    br = road_polygon[2]
    bl = road_polygon[3]

    top_center = ((tl + tr) / 2).astype(np.int32)
    bottom_center = ((bl + br) / 2).astype(np.int32)

    left_zone = np.array([
        tl,
        top_center,
        bottom_center,
        bl
    ], dtype=np.int32)

    center_zone = np.array([
        top_center,
        tr,
        br,
        bottom_center
    ], dtype=np.int32)

    # Делим центр еще раз пополам,
    # чтобы получить 3 зоны
    top_left_center = (
        tl * 2 + tr
    ) // 3

    top_right_center = (
        tl + tr * 2
    ) // 3

    bottom_left_center = (
        bl * 2 + br
    ) // 3

    bottom_right_center = (
        bl + br * 2
    ) // 3

    left_zone = np.array([
        tl,
        top_left_center,
        bottom_left_center,
        bl
    ], dtype=np.int32)

    center_zone = np.array([
        top_left_center,
        top_right_center,
        bottom_right_center,
        bottom_left_center
    ], dtype=np.int32)

    right_zone = np.array([
        top_right_center,
        tr,
        br,
        bottom_right_center
    ], dtype=np.int32)

    return {
        "left": left_zone,
        "center": center_zone,
        "right": right_zone
    }


# =========================
# BBOX / POLYGON
# =========================

def bbox_polygon_overlap_ratio(bbox, polygon):

    x1, y1, x2, y2 = bbox

    width = max(1, int(x2 - x1))
    height = max(1, int(y2 - y1))

    polygon_local = polygon.copy()

    polygon_local[:, 0] -= int(x1)
    polygon_local[:, 1] -= int(y1)

    mask = np.zeros(
        (height, width),
        dtype=np.uint8
    )

    cv2.fillPoly(
        mask,
        [polygon_local],
        255
    )

    intersection = cv2.countNonZero(mask)

    bbox_area = width * height

    return intersection / bbox_area


def is_zone_blocked(
    bbox,
    polygon,
    threshold=ZONE_BLOCK_THRESHOLD
):

    ratio = bbox_polygon_overlap_ratio(
        bbox,
        polygon
    )

    return ratio >= threshold


# =========================
# YOLO BLOCKED ZONES
# =========================

def get_yolo_blocked_zones(
    detections,
    road_zones
):

    left_blocked = False
    center_blocked = False
    right_blocked = False

    for detection in detections:

        bbox_data = detection["bbox"]

        bbox = (
            bbox_data["x1"],
            bbox_data["y1"],
            bbox_data["x2"],
            bbox_data["y2"]
        )

        if is_zone_blocked(
            bbox,
            road_zones["left"]
        ):
            left_blocked = True

        if is_zone_blocked(
            bbox,
            road_zones["center"]
        ):
            center_blocked = True

        if is_zone_blocked(
            bbox,
            road_zones["right"]
        ):
            right_blocked = True

    return (
        left_blocked,
        center_blocked,
        right_blocked
    )


# =========================
# MAIN ANALYSIS
# =========================

def analyze_frame(frame):

    height, width = frame.shape[:2]

    # --------------------------------
    # YOLO
    # --------------------------------

    results = model(
        frame,
        imgsz=IMG_SIZE,
        conf=CONFIDENCE_THRESHOLD,
        verbose=False
    )

    detections = []

    for result in results:

        for box in result.boxes:

            class_id = int(box.cls[0])

            confidence = float(
                box.conf[0]
            )

            x1, y1, x2, y2 = (
                box.xyxy[0].tolist()
            )

            x1 = int(x1)
            y1 = int(y1)
            x2 = int(x2)
            y2 = int(y2)

            center_x = int(
                (x1 + x2) / 2
            )

            center_y = int(
                (y1 + y2) / 2
            )

            class_name = model.names[
                class_id
            ]

            detections.append({
                "class": class_name,

                "confidence": round(
                    confidence,
                    3
                ),

                "bbox": {
                    "x1": x1,
                    "y1": y1,
                    "x2": x2,
                    "y2": y2
                },

                "center": {
                    "x": center_x,
                    "y": center_y
                }
            })

    # --------------------------------
    # ROAD
    # --------------------------------

    road_polygon = create_road_trapezoid(
        width,
        height
    )

    road_zones = create_road_zones(
        road_polygon
    )

    # --------------------------------
    # BLOCKED ZONES
    # --------------------------------

    (
        left_blocked,
        center_blocked,
        right_blocked
    ) = get_yolo_blocked_zones(
        detections,
        road_zones
    )

    # --------------------------------
    # DECISION
    # --------------------------------

    road_ahead_free = not center_blocked

    if not center_blocked:

        avoidance = "not_needed"

    else:

        if not left_blocked and not right_blocked:

            avoidance = "left_or_right"

        elif not left_blocked:

            avoidance = "left"

        elif not right_blocked:

            avoidance = "right"

        else:

            avoidance = "nowhere"

    # --------------------------------
    # RESULT
    # --------------------------------

    return {

        "road_ahead_free":
            road_ahead_free,

        "avoidance":
            avoidance,

        "zones": {
            "left_blocked":
                left_blocked,

            "center_blocked":
                center_blocked,

            "right_blocked":
                right_blocked
        },

        "detections":
            detections,

        "road_polygon":
            road_polygon,

        "road_zones":
            road_zones
    }


# =========================
# TEST
# =========================

if __name__ == "__main__":

    image_path = "image.png"

    frame = cv2.imread(
        image_path
    )

    if frame is None:

        print(
            "Не удалось открыть изображение"
        )

        exit()

    result = analyze_frame(
        frame
    )

    print("\n========== RESULT ==========")

    print(
        "Road ahead free:",
        result["road_ahead_free"]
    )

    print(
        "Avoidance:",
        result["avoidance"]
    )

    print("\nZones:")

    print(
        "Left:",
        result["zones"]["left_blocked"]
    )

    print(
        "Center:",
        result["zones"]["center_blocked"]
    )

    print(
        "Right:",
        result["zones"]["right_blocked"]
    )

    print("\nObjects:")

    for obj in result["detections"]:

        print(
            f'{obj["class"]} '
            f'conf={obj["confidence"]} '
            f'bbox={obj["bbox"]} '
            f'center={obj["center"]}'
        )