"""Мягкая обработка фото номеров — без «дорисовки»: баланс белого, свет и тени, вертикали, единый стиль.

python tools/retouch.py <вход.jpg> <выход.jpg> [--wb 0.6] [--lift 0.3] [--vert 0.85]
python tools/retouch.py --compare std2-1 semi-3 std2-7   — снимки «до | после» в shots/retouch/

Что делает:
  1. Баланс белого — по самым светлым неперегоретым местам кадра (бельё, сантехника, потолочная лампа):
     их оттенок сдвигается к нейтральному на долю --wb; тёплое дерево остаётся тёплым, но не оранжевым.
  2. Тени поднимаются (--lift), светлые места мягко сжимаются — окна меньше «выгорают».
  3. Немного локального контраста (CLAHE по яркости), оранжевые тона чуть спокойнее.
  4. Вертикали: ищутся почти вертикальные линии (углы стен, косяки), кадр выпрямляется на долю --vert,
     края обрезаются, пропорции и размер кадра — как у исходника.
Ничего не добавляет и не убирает из кадра.
"""
import sys
import os
import cv2
import numpy as np


def white_balance(img, strength):
    v = img.max(axis=2)
    ok = v < 0.97
    lum = img.mean(axis=2)
    thr = np.quantile(lum[ok], 0.97) if ok.any() else 1
    sel = ok & (lum >= thr)
    ref = img[sel].mean(axis=0)  # BGR светлых мест
    gain = ref.mean() / np.maximum(ref, 1e-4)
    gain = 1 + (gain - 1) * strength
    out = img * gain[None, None, :]
    return np.clip(out, 0, 1), ref, gain


def tone(img, lift):
    lum = img.mean(axis=2)
    lo, hi = np.quantile(lum, 0.004), np.quantile(lum, 0.996)
    img = np.clip((img - lo) / max(hi - lo, 1e-3), 0, 1)
    # общая экспозиция: середина кадра — к 0,5 (только светлее, не темнее, и не больше чем на треть ступени гаммы)
    med = float(np.median(img.mean(axis=2)))
    g = float(np.clip(np.log(0.5) / np.log(max(med, 1e-3)), 0.75, 1.0))
    img = img ** g
    # подъём теней и мягкое плечо в светлых
    x = img
    x = x + lift * x * (1 - x) ** 2
    x = x - 0.12 * x ** 3 * (1 - x) * 4
    return np.clip(x, 0, 1)


def local_contrast(img, amount=0.35):
    lab = cv2.cvtColor((img * 255).astype(np.uint8), cv2.COLOR_BGR2LAB)
    L = lab[:, :, 0]
    cl = cv2.createCLAHE(clipLimit=1.6, tileGridSize=(8, 8)).apply(L)
    lab[:, :, 0] = (L * (1 - amount) + cl * amount).astype(np.uint8)
    return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR).astype(np.float32) / 255


def calm_orange(img, k=0.9):
    hsv = cv2.cvtColor((img * 255).astype(np.uint8), cv2.COLOR_BGR2HSV).astype(np.float32)
    h, s = hsv[:, :, 0], hsv[:, :, 1]
    w = np.clip(1 - np.abs(h - 15) / 12, 0, 1)  # оранжево-жёлтые (OpenCV: 0..180)
    hsv[:, :, 1] = s * (1 - (1 - k) * w)
    return cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR).astype(np.float32) / 255


def verticals(img, strength):
    H, W = img.shape[:2]
    g = cv2.cvtColor((img * 255).astype(np.uint8), cv2.COLOR_BGR2GRAY)
    e = cv2.Canny(cv2.GaussianBlur(g, (5, 5), 0), 50, 150)
    L = cv2.HoughLinesP(e, 1, np.pi / 720, threshold=120, minLineLength=H // 6, maxLineGap=12)
    if L is None:
        return img, None
    xs, slopes, wts = [], [], []
    for x1, y1, x2, y2 in np.asarray(L).reshape(-1, 4):
        dy = y2 - y1
        if dy == 0:
            continue
        a = (x2 - x1) / dy  # dx/dy
        if abs(a) > 0.22:
            continue
        xs.append((x1 + x2) / 2 - W / 2)
        slopes.append(a)
        wts.append(np.hypot(x2 - x1, dy))
    if len(xs) < 4:
        return img, None
    xs, slopes, wts = map(np.array, (xs, slopes, wts))
    # наклон линии = r + k·x: r — общий наклон (поворот), k — сведение к точке (камера вверх/вниз)
    A = np.stack([np.ones_like(xs), xs], 1) * wts[:, None]
    r, k = np.linalg.lstsq(A, slopes * wts, rcond=None)[0]
    # мягко и с ограничением: поворот не больше ~2°, сведение — не больше 6% по краю кадра
    r = float(np.clip(r * strength, -0.035, 0.035))
    k = float(np.clip(k * strength, -0.12 / H, 0.12 / H))
    cx, cy = W / 2, H / 2

    def src_x(x, y):
        return cx + (x - cx) * (1 + k * (y - cy)) + r * (y - cy)
    # самый большой кадр с центром посередине и теми же пропорциями, где нет пустых краёв
    s_lo, s_hi = 0.5, 1.0
    for _ in range(30):
        s = (s_lo + s_hi) / 2
        hw, hh = W * s / 2, H * s / 2
        ok = all(0 <= src_x(x, y) <= W - 1 for x in (cx - hw, cx + hw) for y in (cy - hh, cy + hh))
        s_lo, s_hi = (s, s_hi) if ok else (s_lo, s)
    s = s_lo
    # выходной пиксель (u, v) → точка обрезанного кадра → исходник
    v, u = np.mgrid[0:H, 0:W].astype(np.float32)
    yc = cy + (v - cy) * s
    xc = cx + (u - cx) * s
    mx = src_x(xc, yc).astype(np.float32)
    out = cv2.remap(img, mx, yc.astype(np.float32), cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)
    return np.clip(out, 0, 1), (round(r, 4), round(k * H / 2, 4), round(1 - s, 3))


def process(src, dst, wb=0.6, lift=0.3, vert=0.85, cool=0.035):
    img = cv2.imdecode(np.fromfile(src, np.uint8), cv2.IMREAD_COLOR).astype(np.float32) / 255
    img, ref, gain = white_balance(img, wb)
    img = tone(img, lift)
    img = local_contrast(img)
    img = calm_orange(img, 0.86)
    img = np.clip(img * np.array([1 + cool, 1, 1 - cool * .8], np.float32)[None, None, :], 0, 1)  # чуть холоднее: меньше оранжевого
    img, vinfo = verticals(img, vert) if vert else (img, None)
    ok, buf = cv2.imencode('.jpg', (img * 255 + .5).astype(np.uint8), [cv2.IMWRITE_JPEG_QUALITY, 90])
    buf.tofile(dst)
    return {'wb_gain_bgr': np.round(gain, 3).tolist(), 'vert(r,k‰,crop)': vinfo}


def compare(names):
    os.makedirs('shots/retouch', exist_ok=True)
    for n in names:
        src = f'src/rooms/{n}.jpg'
        dst = f'shots/retouch/{n}-after.jpg'
        info = process(src, dst)
        a = cv2.imdecode(np.fromfile(src, np.uint8), cv2.IMREAD_COLOR)
        b = cv2.imdecode(np.fromfile(dst, np.uint8), cv2.IMREAD_COLOR)
        h = 900
        a = cv2.resize(a, (int(a.shape[1] * h / a.shape[0]), h)); b = cv2.resize(b, (a.shape[1], h))
        gap = np.full((h, 16, 3), 255, np.uint8)
        cv2.imencode('.jpg', np.hstack([a, gap, b]), [cv2.IMWRITE_JPEG_QUALITY, 86])[1].tofile(f'shots/retouch/{n}-compare.jpg')
        print(n, info)


if __name__ == '__main__':
    if sys.argv[1] == '--compare':
        compare(sys.argv[2:])
    else:
        args = sys.argv[1:]
        opts = {k[2:]: float(v) for k, v in zip(args[2::2], args[3::2])}
        print(process(args[0], args[1], **opts))
