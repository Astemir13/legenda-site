"""Карта глубины с точной границей неба: небо (по глубине) уточняется цветом фото — край кровли, снег на крыше,
сосны и горы получают глубину заведомо больше порога (42), небо — 0. Результат — src/depth.jpg (400×267), сайт берёт его как img/depth.jpg.
Запуск из корня: python tools/sky-mask.py [картинка_маски_для_просмотра.png]"""
import sys
from PIL import Image, ImageFilter
photo = Image.open('src/facade.jpg').convert('RGB')
depth = Image.open('src/facade-depth.jpg').convert('L').resize(photo.size, Image.BICUBIC)
W, H = photo.size
P = photo.load(); D = depth.load()
sky = Image.new('L', photo.size, 0); S = sky.load()
for y in range(H):
    for x in range(W):
        d = D[x, y]
        if d >= 50 or y > H*.42: continue
        r, g, b = P[x, y]
        blue = b - r            # голубое небо
        cloud = min(r, g, b) > 200 and b >= r - 4 and d < 30   # облака — белые, но очень далеко
        if (blue > 22 and b > 120) or cloud: S[x, y] = 255
# убрать одиночные шумы и отступить от края кровли на пару пикселей
sky = sky.filter(ImageFilter.MinFilter(5)).filter(ImageFilter.MaxFilter(3))
out = depth.copy(); O = out.load(); K = sky.load()
for y in range(H):
    for x in range(W):
        O[x, y] = 0 if K[x, y] > 127 else max(D[x, y], 44)
out.save('src/facade-depth-sky.png')
small = out.resize((400, 267), Image.LANCZOS)
small.save('src/depth.jpg', 'JPEG', quality=60, optimize=True)
sky.resize((W // 2, H // 2)).save(sys.argv[1] if len(sys.argv) > 1 else 'skymask_preview.png')
print('ok: src/depth.jpg')
