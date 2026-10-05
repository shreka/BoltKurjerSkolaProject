"""
turn_and_clearance_detector.py

On-demand модуль проверки поворотов и бокового просвета.
Вызывается навигатором ТОЛЬКО в окне ожидания перекрёстка
(например, начиная с ~70% расчётного расстояния по одометрии
до следующей известной точки поворота), а не постоянно в фоне.

Совмещает то, что раньше предполагалось делать двумя разными
программами: "есть ли поворот" + "нет ли стены в этом
направлении" — потому что по факту это один и тот же
физический сигнал (свободное/занятое пространство в зоне).

Возвращает: {"Left": bool, "Right": bool, "Forward": bool}
True = физически свободно и можно ехать в эту сторону.
"""

import cv2

# ---------------- SETTINGS ----------------
PROC_WIDTH = 320            # даунскейл кадра для скорости (было full-res)
CANNY_LOW = 40
CANNY_HIGH = 130

FRAMES_TO_CONFIRM = 3        # сколько подряд кадров должны совпасть
MAX_FRAMES = 8                # предохранитель, если консенсус не набрался

OPEN_DENSITY_MAX = 0.05      # ниже — похоже на открытое пространство
WALL_DENSITY_MIN = 0.09      # выше — похоже на стену/структуру

# Гладкая стена вплотную к камере тоже даёт мало рёбер (нечего
# детектить) — её легко перепутать с открытым полом вдали, если
# смотреть только на плотность рёбер. Поэтому дополнительно
# проверяем текстуру (разброс яркости): у пола/предметов она
# выше, у голой окрашенной стены — почти нулевая.
MIN_TEXTURE_STD = 14.0       # ниже — похоже на гладкую пустую стену

NEAR_BAND = (0.55, 0.85)     # ближняя к роботу полоса (доля высоты кадра)
FAR_BAND = (0.30, 0.55)      # дальняя полоса

ZONES = {
    "Left":    (0.00, 0.38),
    "Forward": (0.32, 0.68),
    "Right":   (0.62, 1.00),
}


# ============================================================
# CORE
# ============================================================

def _resize(frame):
    h, w = frame.shape[:2]
    scale = PROC_WIDTH / w
    return cv2.resize(frame, (PROC_WIDTH, int(h * scale)),
                       interpolation=cv2.INTER_AREA)


def _edges(gray):
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    g = clahe.apply(gray)
    g = cv2.GaussianBlur(g, (5, 5), 0)
    return cv2.Canny(g, CANNY_LOW, CANNY_HIGH)


def _density(edges, x1, x2, y1, y2):
    h, w = edges.shape
    x1, x2 = max(0, int(x1)), min(w, int(x2))
    y1, y2 = max(0, int(y1)), min(h, int(y2))
    if x2 <= x1 or y2 <= y1:
        return 1.0
    region = edges[y1:y2, x1:x2]
    return cv2.countNonZero(region) / region.size


def _texture_std(gray, x1, x2, y1, y2):
    h, w = gray.shape
    x1, x2 = max(0, int(x1)), min(w, int(x2))
    y1, y2 = max(0, int(y1)), min(h, int(y2))
    if x2 <= x1 or y2 <= y1:
        return 0.0
    return float(gray[y1:y2, x1:x2].std())


def _zone_open(edges, gray, x_range):
    """
    Проверка зоны по двум полосам (near/far) + текстуре.

    ВАЖНО: гладкая пустая стена вплотную к камере тоже даёт мало
    рёбер — по одной лишь плотности рёбер её не отличить от
    открытого пола вдали. Поэтому near-полоса дополнительно
    проверяется на текстуру (variance яркости): у пола/предметов
    она заметная, у голой стены — почти нулевая. Зона считается
    открытой, только если она И малоплотная по рёбрам, И не
    выглядит как гладкая поверхность в упор.

    Никакого "доверяем дальней полосе, если ближняя пустая" —
    это раньше давало ложные срабатывания именно на гладких стенах.
    """
    h, w = edges.shape
    x1, x2 = x_range[0] * w, x_range[1] * w

    near = _density(edges, x1, x2, h * NEAR_BAND[0], h * NEAR_BAND[1])
    far = _density(edges, x1, x2, h * FAR_BAND[0], h * FAR_BAND[1])
    near_texture = _texture_std(gray, x1, x2, h * NEAR_BAND[0], h * NEAR_BAND[1])

    near_ok = (near < OPEN_DENSITY_MAX) and (near_texture > MIN_TEXTURE_STD)
    far_ok = far < WALL_DENSITY_MIN

    return (near_ok and far_ok), near, far


def analyze_frame(frame):
    small = _resize(frame)
    gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
    edges = _edges(gray)

    result, raw = {}, {}
    for name, xr in ZONES.items():
        open_, near, far = _zone_open(edges, gray, xr)
        result[name] = open_
        raw[name] = (near, far)

    return result, edges, raw


# ============================================================
# REAL-TIME ВЕРСИЯ (не одиночный кадр, а поток с накоплением
# истории, привязанной к пройденному расстоянию по одометрии)
# ============================================================
#
# Одиночный кадр НЕЛЬЗЯ надёжно классифицировать на сценах типа
# "гладкая стена под острым углом" — плотность рёбер/текстура на
# таких кадрах пограничные и будут иногда давать false positive
# независимо от подбора порогов. Пока робот физически едет, у нас
# есть поток кадров + одометрия — этим и пользуемся: решение
# принимается только если сигнал стабилен на протяжении заметного
# пройденного расстояния, а не одного случайного кадра.

class TurnDetector:
    """
    Использование в цикле навигации (каждую итерацию, пока едем
    в окне ожидания перекрёстка):

        det = TurnDetector(expected={"Left": True, "Right": False,
                                      "Forward": True})

        while approaching_intersection:
            frame = get_frame_from_camera()
            ticks = read_odometry_ticks()          # с Arduino по BLE
            det.update(frame, ticks)

            if det.is_confident():
                result = det.result()
                break   # можно принимать решение о повороте

    ticks должен быть монотонно растущим счётчиком пройденного
    расстояния (пауза во время объезда препятствий — на стороне
    навигатора, как обсуждали раньше).
    """

    def __init__(self, expected=None,
                 min_distance_ticks=40,   # минимум "пройдено" для доверия
                 history_len=25):
        self.expected = expected or {k: True for k in ZONES}
        self.min_distance_ticks = min_distance_ticks
        self.history_len = history_len

        self.history = {k: [] for k in ZONES}   # (ticks, bool)
        self.last_edges = None

    def update(self, frame, ticks):
        if frame is None:
            return

        res, edges, _ = analyze_frame(frame)
        self.last_edges = edges

        for k in ZONES:
            if not self.expected.get(k, True):
                continue
            hist = self.history[k]
            hist.append((ticks, res[k]))
            if len(hist) > self.history_len:
                hist.pop(0)

    def is_confident(self):
        """
        True, если по каждому активному направлению набралось
        достаточно пройденного расстояния (не кадров!) с
        одинаковым, устойчивым результатом.
        """
        for k in ZONES:
            if not self.expected.get(k, True):
                continue
            hist = self.history[k]
            if len(hist) < FRAMES_TO_CONFIRM:
                return False

            ticks_span = hist[-1][0] - hist[0][0]
            if ticks_span < self.min_distance_ticks:
                return False  # проехали слишком мало для доверия

            recent = [v for _, v in hist[-FRAMES_TO_CONFIRM:]]
            if len(set(recent)) != 1:
                return False  # результат ещё скачет

        return True

    def result(self):
        final = {k: False for k in ZONES}
        for k in ZONES:
            hist = self.history[k]
            if not hist:
                continue
            values = [v for _, v in hist]
            true_ratio = sum(values) / len(values)
            final[k] = true_ratio >= 0.7  # чуть строже, чем раньше
        return final


# Обёртка для теста без реальной камеры / одного фото — оставлена
# для совместимости, но для реальной езды используй TurnDetector.
def check_directions(get_frame_fn, expected=None, max_frames=MAX_FRAMES):
    votes = {k: [] for k in ZONES if (expected or {}).get(k, True)}
    last_edges = None

    for _ in range(max_frames):
        frame = get_frame_fn()
        if frame is None:
            continue
        res, edges, _ = analyze_frame(frame)
        last_edges = edges
        for k in votes:
            votes[k].append(res[k])

    final = {k: False for k in ZONES}
    for k, v in votes.items():
        if v:
            final[k] = (sum(v) / len(v)) >= 0.7
    return final, last_edges


# ============================================================
# DEBUG BLOCK — можно целиком удалить, ничего снаружи
# на него не ссылается.
# ============================================================
DEBUG = True

if DEBUG:
    def save_debug_image(frame, result, path="debug_turn.jpg"):
        vis = _resize(frame).copy()
        h, w = vis.shape[:2]

        for name, xr in ZONES.items():
            x1, x2 = int(xr[0] * w), int(xr[1] * w)
            color = (0, 200, 0) if result.get(name) else (0, 0, 200)
            cv2.rectangle(vis, (x1, int(h * FAR_BAND[0])),
                          (x2, int(h * NEAR_BAND[1])), color, 2)
            cv2.putText(vis, f"{name}:{result.get(name)}",
                        (x1 + 4, int(h * FAR_BAND[0]) + 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2)

        cv2.imwrite(path, vis)
        return path


# ============================================================
# ПРИМЕР ИСПОЛЬЗОВАНИЯ (для теста на одном фото)
# ============================================================

if __name__ == "__main__":
    # ВНИМАНИЕ: тест на одном статичном фото — это НЕ то, как модуль
    # должен использоваться в реальной езде (см. TurnDetector выше).
    # Здесь просто быстрая sanity-проверка, что код не падает.
    import sys

    path = sys.argv[1] if len(sys.argv) > 1 else "turn.jpg"
    frame = cv2.imread(path)

    if frame is None:
        print(f"ERROR: не могу открыть {path}")
        sys.exit(1)

    res, edges, _ = analyze_frame(frame)
    print("Одиночный кадр (не показатель реальной точности):", res)

    if DEBUG:
        save_debug_image(frame, res)