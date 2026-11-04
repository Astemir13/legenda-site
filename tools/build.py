"""Собирает из исходника src/legenda-template.html:
  1) dist/tilda-blok-1.html и dist/tilda-blok-2.html — код для двух блоков T123 на Тильде;
  2) index.html — живой предпросмотр с панелью погоды (GitHub Pages).
Особенности файла для Тильды:
- все стили под #lg (Тильда просит не трогать общие теги);
- без панели «Погода: демо», погода только реальная, без неё плашки скрываются;
- фото по ссылке вместо вшитого;
- заглушки в [скобках] убраны вместе с блоками, где их нечем заменить.
Запуск из корня репозитория: python3 tools/build.py [ссылка_на_фото_в_Тильде]"""
import re, sys

SRC = 'src/legenda-template.html'
OUT1 = 'dist/tilda-blok-1.html'
OUT2 = 'dist/tilda-blok-2.html'
PREVIEW = 'index.html'
PHOTO = sys.argv[1] if len(sys.argv) > 1 else 'ССЫЛКА_НА_ФОТО_ФАСАДА'
# панель «Погода» на /new — чтобы владелец переключал погоды с телефона; когда /new станет главной — False
DEMO = True

t = open(SRC, encoding='utf-8').read()
# предпросмотр: исходник как есть, фото — файлом рядом
open(PREVIEW, 'w', encoding='utf-8', newline='\n').write(
    '<!doctype html>\n<html lang="ru">\n<meta charset="utf-8">\n<meta name="robots" content="noindex">\n'
    + t.replace('__FACADE__', 'src/facade.jpg'))
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
# стили панели «Погода» — отдельно: в блоке 1 нет места, они уходят в блок 2 (или вовсе выкидываются)
PANEL_RE = re.compile(r'\.wx(?:panel|x|btns|body|note|h|kinds|phases)\b|#wxMode')
css_lines = css.split('\n')
panel_css = '\n'.join(l for l in css_lines if PANEL_RE.search(l))
css = '\n'.join(l for l in css_lines if not PANEL_RE.search(l))

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
panel_css = prefix(panel_css)
css = css.replace('#lg{scroll-behavior:smooth;', '#lg{')  # html{scroll-behavior} -> через JS
css += '\n#lg.nowx .now,#lg.nowx .wxchip{display:none}\n#lg{min-height:100vh;position:relative}\n'

# ---------- Разметка ----------
panel_html = re.search(r'<details class="wxpanel".*?</details>\n', body, re.S).group(0)
body = body.replace(panel_html, '')
body = must(body, '<img src="__FACADE__"', '<img src="' + PHOTO + '" fetchpriority="high"')
# заглушки
body = re.sub(r'<section class="sec" id="reviews".*?</section>\n\n', '', body, flags=re.S)
body = must(body, '<a href="#reviews">Отзывы</a>', '')
body = re.sub(r'\s*<a href="#reviews">.*?Отзывы гостей</a>', '', body, flags=re.S)
body = must(body, ' — сауна ([цена]) и партия', ' — сауна и партия')
body = must(body, ' (за питомца [доплата])', '')
body = re.sub(r'\s*<div><span>[^<]*</span><span>\[[^\]]*\][^<]*</span></div>', '', body)
body = re.sub(r'<section class="sec" id="faq".*?</section>\n\n', '', body, count=1, flags=re.S)
body = re.sub(r'\s*<li data-ph>.*?</li>', '', body)
assert '[' not in re.sub(r'<script.*?</script>', '', body, flags=re.S).replace('[open]', ''), re.findall(r'.{40}\[[^\]]*\].{20}', body)
body = '<div id="lg" class="nowx">' + body.strip() + '\n</div>'

# ---------- Скрипт ----------
assert js.lstrip().startswith('(function(){')
js = js.replace("(function(){\n", "(function(){\n  var LG = document.getElementById('lg'); document.documentElement.style.scrollBehavior = 'smooth';\n", 1)
js = must(js, "r = document.documentElement.style;", "r = LG.style;")
js = must(js, "var PREVIEW = true;", "var PREVIEW = false;")
js = must(js, "W.live = true; W.temp", "LG.classList.remove('nowx'); W.live = true; W.temp")
js = must(js, "    }).catch(function(){\n      W.live = false;", "    }).catch(function(){\n      if (W.live) return; LG.classList.add('nowx');\n      W.live = false;")
if DEMO:
    # панель стоит в блоке 2, а стили у неё под #lg — переносим её внутрь
    js = js.replace("var LG = document.getElementById('lg');", "var LG = document.getElementById('lg'); LG.appendChild(document.getElementById('wxPanel'));", 1)
else:
    js = re.sub(r"    document\.getElementById\('wxMode'\).*?\n", '', js)
    js = re.sub(r"    document\.querySelectorAll\('\[data-(?:k|ph)\]'\).*?\n", '', js)
    js = re.sub(r"      document\.getElementById\('wxNote'\).*?\n", '', js)
    js = re.sub(r"  /\* Закрыть панель погоды.*?\n(?:  .*wxp.*\n)+", '', js)
    js = re.sub(r"  /\* Панель предпросмотра погоды \*/\n(?:  .*\n){6}", '', js)
    for bad in ('wxMode', 'wxNote', 'wxKinds', 'wxPanel', 'wxAuto', 'wxClose'):
        assert bad not in js, bad
assert 'wxPanel' not in body

# Тильда не сохраняет блок T123 больше ~120 000 знаков, поэтому код делится на два блока:
# 1) шрифты, стили и разметка; 2) скрипт. На странице блок 1 должен стоять выше блока 2.
import json
parts = {
    OUT1: '<!-- Эко-отель «Легенда» · главная · блок 1 из 2 (стили и разметка). Блок 2 со скриптом стоит сразу под ним. -->\n'
          + fonts + '\n<style>\n' + css + '</style>\n' + body + '\n',
    OUT2: '<!-- Эко-отель «Легенда» · главная · блок 2 из 2 (скрипт). Ставится сразу под блоком 1. -->\n'
          + ('<style>\n' + panel_css + '</style>\n' + panel_html if DEMO else '')
          + '<script>\n' + js + '</script>\n',
}
for path, code in parts.items():
    n = len(json.dumps(code, ensure_ascii=False))
    assert n < 110000, (path, n, 'блок не влезет в T123 — лимит Тильды около 120 000 знаков')
    open(path, 'w', encoding='utf-8', newline='\n').write(code)
    print(path, len(code), 'знаков')
print(PREVIEW, 'обновлён')
