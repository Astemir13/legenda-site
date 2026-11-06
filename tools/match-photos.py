"""Какому оригиналу (photos-orig/) соответствует каждое фото на сайте (src/rooms/), и какие оригиналы на сайт не попали.

python tools/match-photos.py   → таблица в консоли и photos-orig/_map.json, листы миниатюр в shots/orig/
Сравнение — по маленьким серым копиям (корреляция), с учётом того, что на сайте кадр мог быть немного обрезан.
"""
import glob
import json
import os
import cv2
import numpy as np


def load(path, w=64):
    im = cv2.imdecode(np.fromfile(path, np.uint8), cv2.IMREAD_COLOR)  # с учётом поворота из EXIF
    h = int(im.shape[0] * w / im.shape[1])
    return cv2.resize(im, (w, h), interpolation=cv2.INTER_AREA), im.shape[:2]


def feat(im, size=(48, 64)):
    g = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY).astype(np.float32)
    g = cv2.resize(g, size, interpolation=cv2.INTER_AREA)
    g = (g - g.mean()) / (g.std() + 1e-6)
    return g


def score(a, b):
    # оба приводим к одной пропорции (портрет 3:4), плюс пробуем небольшие обрезки оригинала
    best = -2
    fa = feat(a)
    H, W = b.shape[:2]
    for c in (0, 0.03, 0.06, 0.1):
        y0, x0 = int(H * c / 2), int(W * c / 2)
        bb = b[y0:H - y0, x0:W - x0]
        best = max(best, float((fa * feat(bb)).mean()))
    return best


site = sorted(glob.glob('src/rooms/*.jpg'))
orig = sorted(glob.glob('photos-orig/*.*'))
S = {p: load(p) for p in site}
O = {p: load(p) for p in orig}
res, used = {}, {}
for s, (sa, _) in S.items():
    sc = sorted(((score(sa, oa), o) for o, (oa, _) in O.items() if (oa.shape[0] > oa.shape[1]) == (sa.shape[0] > sa.shape[1])), reverse=True)
    best = sc[0]
    res[os.path.basename(s)] = {'orig': os.path.basename(best[1]), 'score': round(best[0], 3), 'second': round(sc[1][0], 3)}
    used.setdefault(best[1], []).append(os.path.basename(s))
for k, v in res.items():
    print(f"{k:12} ← {v['orig']:58} {v['score']:.2f} (след. {v['second']:.2f})")
unused = [os.path.basename(o) for o in orig if o not in used]
dup = {os.path.basename(k): v for k, v in used.items() if len(v) > 1}
print('\nоригиналов не на сайте:', len(unused), '| одному оригиналу соответствует несколько фото сайта:', dup)
json.dump({'site': res, 'unused': unused, 'sizes': {os.path.basename(o): list(O[o][1]) for o in orig}}, open('photos-orig/_map.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

# листы миниатюр: оригиналы, которых нет на сайте
os.makedirs('shots/orig', exist_ok=True)
tw, th = 300, 400
cols = 6
names = unused
for page in range(0, len(names), 24):
    chunk = names[page:page + 24]
    rows = (len(chunk) + cols - 1) // cols
    sheet = np.full((rows * (th + 34), cols * tw, 3), 255, np.uint8)
    for i, n in enumerate(chunk):
        im = cv2.imdecode(np.fromfile('photos-orig/' + n, np.uint8), cv2.IMREAD_COLOR)
        s = min(tw / im.shape[1], th / im.shape[0])
        t = cv2.resize(im, (int(im.shape[1] * s), int(im.shape[0] * s)), interpolation=cv2.INTER_AREA)
        y, x = (i // cols) * (th + 34), (i % cols) * tw
        sheet[y:y + t.shape[0], x:x + t.shape[1]] = t
        cv2.putText(sheet, f'{page + i + 1}', (x + 6, y + th + 26), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (30, 30, 30), 2)
    cv2.imencode('.jpg', sheet, [cv2.IMWRITE_JPEG_QUALITY, 80])[1].tofile(f'shots/orig/unused-{page // 24 + 1}.jpg')
print('листы:', sorted(glob.glob('shots/orig/unused-*.jpg')))
