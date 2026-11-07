"""Обработать все фото номеров из оригиналов (photos-orig/) стилем warm — для выбора владельцем.

python tools/retouch-all.py
  photos-orig/warm/<номер>-<N>.jpg — обработанные, до 1800 px, готовы заменить src/rooms/ (менять — только выбранные владельцем)
  shots/retouch/review-<номер>.jpg  — листы «как сейчас | после» с подписями, по категориям
Фото, для которых оригинал не найден уверенно (совпадение < 0,9), не обрабатываются — остаются как есть.
"""
import json
import os
import sys
import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from retouch import process

M = json.load(open('photos-orig/_map.json', encoding='utf-8'))['site']
os.makedirs('photos-orig/warm', exist_ok=True)
os.makedirs('shots/retouch', exist_ok=True)
done, skipped = [], []
for name, m in sorted(M.items()):
    if m['score'] < 0.9:
        skipped.append(name); continue
    full = 'photos-orig/warm/_full.jpg'
    process('photos-orig/' + m['orig'], full, style='warm', vert=0.9)
    im = cv2.imdecode(np.fromfile(full, np.uint8), cv2.IMREAD_COLOR)
    s = min(1, 1800 / max(im.shape[:2]))
    if s < 1:
        im = cv2.resize(im, (int(im.shape[1] * s), int(im.shape[0] * s)), interpolation=cv2.INTER_AREA)
    cv2.imencode('.jpg', im, [cv2.IMWRITE_JPEG_QUALITY, 90])[1].tofile('photos-orig/warm/' + name)
    done.append(name)
    print('ok', name)
os.remove('photos-orig/warm/_full.jpg')

# листы для выбора: по категории, в каждой строке «сейчас | после» и подпись
def tile(path, h):
    im = cv2.imdecode(np.fromfile(path, np.uint8), cv2.IMREAD_COLOR)
    return cv2.resize(im, (int(im.shape[1] * h / im.shape[0]), h), interpolation=cv2.INTER_AREA)


cats = {}
for n in done:
    cats.setdefault(n.split('-')[0], []).append(n)
for cat, names in cats.items():
    rows = []
    for n in sorted(names, key=lambda x: int(x.split('-')[1].split('.')[0])):
        h = 520
        a, b = tile('src/rooms/' + n, h), tile('photos-orig/warm/' + n, h)
        lab = np.full((56, a.shape[1] + 14 + b.shape[1], 3), 255, np.uint8)
        cv2.putText(lab, n[:-4] + '   (left: now / right: after)', (8, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.1, (20, 20, 20), 2)
        rows.append(np.vstack([lab, np.hstack([a, np.full((h, 14, 3), 255, np.uint8), b])]))
    w = max(r.shape[1] for r in rows)
    rows = [np.hstack([r, np.full((r.shape[0], w - r.shape[1], 3), 255, np.uint8)]) for r in rows]
    sheet = np.vstack([np.vstack([r, np.full((24, w, 3), 255, np.uint8)]) for r in rows])
    cv2.imencode('.jpg', sheet, [cv2.IMWRITE_JPEG_QUALITY, 82])[1].tofile(f'shots/retouch/review-{cat}.jpg')
print('обработано:', len(done), '| пропущено (оригинал не найден уверенно):', skipped)
