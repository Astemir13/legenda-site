"""Карта глубины с точной границей неба: небо (по глубине) уточняется цветом фото — край кровли, снег на крыше,
сосны и горы получают глубину заведомо больше порога (42), небо — 0. Результат — src/depth.jpg (400×267), сайт берёт его как img/depth.jpg.
Запуск из корня: python tools/sky-mask.py [картинка_маски_для_просмотра.png]"""
import sys
from PIL import Image, ImageFilter
photo = Image.open('src/facade.jpg').convert('RGB')
depth = Image.open('src/facade-depth.jpg').convert('L').resize(photo.size, Image.BICUBIC)
W, H = photo.size
P = photo.load(); D = depth.load()
# хребет гор за левым крылом дома (точки по фото 2000×1333): затенённые склоны по цвету почти как небо у горизонта,
# без этой линии верх склонов попадал в маску и синел пятнами — гора выглядела «серыми кусками» (владелец, 11.11.2026)
RIDGE = [(600, 352), (660, 356), (690, 347), (725, 342), (770, 340), (795, 342), (840, 350), (880, 360), (920, 366), (960, 371), (990, 375), (1020, 378), (1060, 382), (1120, 388)]
def ridge(x):
    if x < RIDGE[0][0] or x > RIDGE[-1][0]: return None
    for (xa, ya), (xb, yb) in zip(RIDGE, RIDGE[1:]):
        if xa <= x <= xb: return ya + (yb - ya)*(x - xa)/(xb - xa)
sky = Image.new('L', photo.size, 0); S = sky.load()
for y in range(H):
    for x in range(W):
        d = D[x, y]
        if d >= 50 or y > H*.42: continue
        ry = ridge(x)
        if ry is not None and y >= ry - 1: continue
        r, g, b = P[x, y]
        blue = b - r            # голубое небо
        cloud = min(r, g, b) > 200 and b >= r - 4 and d < 30   # облака — белые, но очень далеко
        if (blue > 22 and b > 120) or cloud: S[x, y] = 255
# убрать одиночные шумы и отступить от края кровли на пару пикселей
sky = sky.filter(ImageFilter.MinFilter(5)).filter(ImageFilter.MaxFilter(3))
# просветы неба между ветвями сосен — отдельные островки: при тонировке ясного неба они становились синими пятнами
# в кронах (владелец, 11.11.2026). Небом считаем только крупные связные области (от 2% самой большой)
K = sky.load(); seen = bytearray(W*H); comps = []
for y0 in range(H):
    for x0 in range(W):
        if K[x0, y0] <= 127 or seen[y0*W + x0]: continue
        st = [(x0, y0)]; seen[y0*W + x0] = 1; px = []
        while st:
            x, y = st.pop(); px.append((x, y))
            for nx, ny in ((x+1, y), (x-1, y), (x, y+1), (x, y-1)):
                if 0 <= nx < W and 0 <= ny < H and not seen[ny*W + nx] and K[nx, ny] > 127:
                    seen[ny*W + nx] = 1; st.append((nx, ny))
        comps.append(px)
big = max((len(c) for c in comps), default=0)
for c in comps:
    if len(c) < big*.02:
        for x, y in c: K[x, y] = 0
print('островков неба убрано:', sum(1 for c in comps if len(c) < big*.02), 'из', len(comps))
out = depth.copy(); O = out.load(); K = sky.load()
for y in range(H):
    for x in range(W):
        O[x, y] = 0 if K[x, y] > 127 else max(D[x, y], 44)
out.save('src/facade-depth-sky.png')
small = out.resize((400, 267), Image.LANCZOS)
small.save('src/depth.jpg', 'JPEG', quality=60, optimize=True)
# Подробная маска для тонировки ясного неба (img/sky.jpg): сплошное небо — чётко, как выше, а просветы между ветвями
# сосен — мягко, по цвету самого фото, пиксель в пиксель (карта глубины 400 px размывала их в круглые пятна).
# Порог по голубизне (синий минус красный): чистое небо 90–120, у горизонта 40–90, снег на ветках — около нуля.
# Горы ниже линии хребта исключены, ниже середины кадра неба нет.
# правое крыло дома (крыша со снегом рядом с правой сосной): в мягкую маску не входит
HOUSE_R = [(1600, 280), (1852, 324), (1922, 512), (1918, 560), (1932, 662), (1932, 1333), (1600, 1333)]
def inside(x, y, poly):
    c = False; j = len(poly) - 1
    for i in range(len(poly)):
        xi, yi = poly[i]; xj, yj = poly[j]
        if (yi > y) != (yj > y) and x < (xj - xi)*(y - yi)/(yj - yi) + xi: c = not c
        j = i
    return c
def ramp(v, a, b): return 0. if v <= a else 1. if v >= b else (v - a)/(b - a)
soft = Image.new('L', photo.size, 0); SO = soft.load()
for y in range(int(H*.56)):
    fy = 1 - ramp(y, H*.46, H*.56)
    for x in range(W):
        if K[x, y] > 127: SO[x, y] = 255; continue
        r, g, b = P[x, y]
        a = ramp(b - r, 32, 62)*ramp(b, 150, 200)
        if not a: continue
        ry = ridge(x)
        if ry is not None: a *= ramp(ry - y, 0, 3)
        a *= max(1 - ramp(x, 760, 800), ramp(x, 1760, 1800))   # просветы — только в кронах у левого и правого края (не снег на крыше)
        if a and x > 1600 and inside(x, y, HOUSE_R): a = 0
        SO[x, y] = int(255*a*fy)
# склоны гор ниже хребта — ровный лёгкий тон (около трети от неба): без него на фоне синего неба гора выглядела серой,
# а когда в маску попадал только верх склонов — пятнистой. Снизу гору закрывают крыша левого крыла и сосны
def roof_y(x): return 520 if x < 820 else 447 + (377 - 447)*(x - 820)/(1120 - 820)
for x in range(RIDGE[0][0], RIDGE[-1][0] + 1):
    ry = ridge(x); by = roof_y(x)
    for y in range(int(ry) - 3, int(by)):
        r, g, b = P[x, y]; lum = (r + g + b)/3
        m = 100*ramp(y, ry - 3, ry + 3)*ramp(lum, 120, 170)*(1 - ramp(y, by - 6, by))
        if m > SO[x, y]: SO[x, y] = int(m)
soft = soft.filter(ImageFilter.GaussianBlur(.6))
soft.resize((1600, 1066), Image.LANCZOS).save('src/static/img/sky.jpg', 'JPEG', quality=80, optimize=True)
sky.resize((W // 2, H // 2)).save(sys.argv[1] if len(sys.argv) > 1 else 'skymask_preview.png')
soft.resize((W // 2, H // 2)).save('shots/skysoft_preview.png')
print('ok: src/depth.jpg, src/static/img/sky.jpg')
