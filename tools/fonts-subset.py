"""Облегчает латинские наборы шрифтов: оставляет только знаки, которые встречаются на сайте
(латиница, цифры, знаки препинания, ₽ и стрелки). Кириллические наборы не трогает.
Исходные файлы — src/fonts-orig/, результат — src/static/fonts/. Нужны: pip install fonttools brotli
Запуск из корня: python tools/fonts-subset.py"""
import os, glob
from fontTools import subset
from fontTools.ttLib import TTFont
# всё печатное из ASCII, неразрывный пробел, « » ° ² · × … — – ‘ ’ “ ” • ‹ › ← ↑ → ↓ − ★ © ® ½ и знак рубля
KEEP = list(range(0x20, 0x7F)) + [0xA0, 0xA9, 0xAE, 0xBD, 0xAB, 0xBB, 0xB0, 0xB2, 0xB7, 0xD7, 0x2009, 0x2013, 0x2014, 0x2018, 0x2019, 0x201C, 0x201D,
        0x201E, 0x2022, 0x2026, 0x2039, 0x203A, 0x2190, 0x2191, 0x2192, 0x2193, 0x2212, 0x2605, 0x20BD]
for src in sorted(glob.glob('src/fonts-orig/*.woff2')):
    name = os.path.basename(src); dst = 'src/static/fonts/' + name
    if 'cyrillic' in name: continue
    o = subset.Options(); o.flavor = 'woff2'; o.layout_features = ['*']; o.notdef_outline = True
    f = TTFont(src); s = subset.Subsetter(o); s.populate(unicodes=KEEP); s.subset(f); f.flavor = 'woff2'; f.save(dst)
    print(name, os.path.getsize(src), '->', os.path.getsize(dst), 'знаков', len(TTFont(dst).getBestCmap()))
