"""Собирает из исходника src/legenda-template.html:
  1) dist/legenda-tilda.html — файл для блока T123 на Тильде;
  2) index.html — живой предпросмотр с панелью погоды (GitHub Pages).
Особенности файла для Тильды:
- все стили под #lg (Тильда просит не трогать общие теги);
- без панели «Погода: демо», погода только реальная, без неё плашки скрываются;
- фото по ссылке вместо вшитого;
- заглушки в [скобках] убраны вместе с блоками, где их нечем заменить.
Запуск из корня репозитория: python3 tools/build.py [ссылка_на_фото_в_Тильде]"""
import re, sys, json

SRC = 'src/legenda-template.html'
OUT = 'dist/legenda-tilda.html'
PREVIEW = 'index.html'
PREVIEW_PHOTO = 'src/facade-winter-v1.webp'
PHOTO = sys.argv[1] if len(sys.argv) > 1 else 'https://static.tildacdn.com/tild3830-6435-4264-b736-623337616333/5440642714493384044.jpg'

from pathlib import Path

t = Path(SRC).read_text(encoding='utf-8')
redesign = Path('src/redesign.css').read_text(encoding='utf-8')
t = t.replace('</style>', redesign + '\n</style>', 1)
Path(PREVIEW).write_text('<!doctype html>\n<html lang="ru">\n<meta charset="utf-8">\n<meta name="robots" content="noindex">\n' + t.replace('__FACADE__', PREVIEW_PHOTO), encoding='utf-8')
fonts = re.search(r'<link rel="preconnect".*?display=swap">', t, re.S).group(0)
css = re.search(r'<style>(.*?)</style>', t, re.S).group(1)
js = re.search(r'<script>(.*?)</script>', t, re.S).group(1)
body = t[t.index('</style>') + len('</style>'):t.index('<script>')]

def must(s, a, b, n=1):
    c = s.count(a)
    assert c == n, (a[:80], c)
    return s.replace(a, b)

# ---------- CSS: префикс #lg ----------
css = re.sub(r'/\*.*?\*/', '', css, flags=re.S)

def pref_sel(sel):
    out = []
    for s in sel.split(','):
        s = s.strip()
        if not s:
            continue
        if s in ('html', 'body', ':root'):
            out.append('#lg')
        elif s.startswith('body::') or s.startswith('body:'):
            out.append('#lg' + s[4:])
        elif s.startswith(':root'):
            out.append('#lg' + s[5:])
        else:
            out.append('#lg ' + s)
    return ','.join(out)

def block_end(s, i):  # i = index of '{'
    d = 0
    for j in range(i, len(s)):
        if s[j] == '{': d += 1
        elif s[j] == '}':
            d -= 1
            if d == 0: return j
    raise ValueError('unbalanced')

def prefix(s):
    out, i = [], 0
    while True:
        j = s.find('{', i)
        if j < 0:
            out.append(s[i:]); break
        head = s[i:j].strip()
        k = block_end(s, j)
        inner = s[j + 1:k]
        if head.startswith('@media') or head.startswith('@supports'):
            out.append(head + '{' + prefix(inner) + '}')
        elif head.startswith('@'):
            out.append(head + '{' + inner + '}')
        else:
            out.append(pref_sel(head) + '{' + inner + '}')
        out.append('\n')
        i = k + 1
    return ''.join(out)

css = prefix(css)
css = css.replace('#lg{scroll-behavior:smooth;', '#lg{')  # html{scroll-behavior} -> через JS


# Local preview and Tilda share the same content and behavior.
# Exported photographs use their original official hotel CDN URLs.
body = '<div id="lg">' + body.strip() + '\n</div>'
body = body.replace('__FACADE__', PHOTO)
# Summer generation remains local until an explicit publishing request.
body = re.sub(r'<img id="heroSummer"[^>]*>\n?', '', body)
assets = {
    'src/hotel-evening.webp': 'https://static.tildacdn.com/tild6262-6132-4366-a530-653366333066/L6.jpg',
    'src/room-01.webp': 'https://static.tildacdn.com/tild3362-6536-4332-b164-326333386236/IMG_8105_-fotor-2025.jpg',
    'src/room-02.webp': 'https://static.tildacdn.com/tild3437-6339-4534-a466-363666653961/IMG_8122-2_-fotor-20.jpg',
}
for local, remote in assets.items():
    body = body.replace(local, remote)
room_sources = json.loads(Path('src/room-photo-sources.json').read_text(encoding='utf-8'))
# Card image URLs are constructed by JavaScript; use CDN assets in the Tilda export.
photo_urls = {key: item['url'] for key, item in room_sources.items()}
js = js.replace('src="src/room-retouched-v2/\'+r.id+\'.webp"', 'src="\'+(' + json.dumps(photo_urls) + ')[r.id]+\'"')
js = js.replace('(function(){\n', "(function(){\n  var LG = document.getElementById('lg');\n", 1)
js = js.replace('var PREVIEW = true;', 'var PREVIEW = false;')
js = js.replace('document.documentElement.style', 'LG.style')
js = js.replace('getComputedStyle(document.documentElement)', 'getComputedStyle(LG)')
js = js.replace('document.documentElement.classList', 'LG.classList')
css = css.replace('#lg .weather-ready ', '#lg.weather-ready ').replace('#lg .weather-tools ', '#lg.weather-tools ')
out = ('<!-- Эко-отель «Легенда» · локальный редизайн · блок T123. -->\n'
       + fonts + '\n<style>\n' + css + '</style>\n' + body + '\n<script>\n' + js + '</script>\n')
Path(OUT).write_text(out, encoding='utf-8')
print(OUT, len(out.encode()), 'bytes;', PREVIEW, 'updated')
