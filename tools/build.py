"""Собирает из исходника src/legenda-template.html:
  1) dist/legenda-tilda.html — файл для блока T123 на Тильде;
  2) index.html — живой предпросмотр с панелью погоды (GitHub Pages).
Особенности файла для Тильды:
- все стили под #lg (Тильда просит не трогать общие теги);
- без панели «Погода: демо», погода только реальная, без неё плашки скрываются;
- фото по ссылке вместо вшитого;
- заглушки в [скобках] убраны вместе с блоками, где их нечем заменить.
Запуск из корня репозитория: python3 tools/build.py [ссылка_на_фото_в_Тильде]"""
import re, sys

SRC = 'src/legenda-template.html'
OUT = 'dist/legenda-tilda.html'
PREVIEW = 'index.html'
PHOTO = sys.argv[1] if len(sys.argv) > 1 else 'ССЫЛКА_НА_ФОТО_ФАСАДА'

t = open(SRC, encoding='utf-8').read()
# предпросмотр: исходник как есть, фото — файлом рядом
open(PREVIEW, 'w', encoding='utf-8').write(
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
css += '\n#lg .facts{grid-template-columns:repeat(2,minmax(0,1fr));max-width:640px}\n@media (min-width:861px){#lg .why{grid-template-columns:repeat(2,minmax(0,1fr))}}\n#lg .fact-lift{grid-column:auto}\n#lg .nowx-hide{}\n#lg.nowx .now,#lg.nowx .wxchip{display:none}\n#lg{min-height:100vh;position:relative}\n'

# ---------- Разметка ----------
body = re.sub(r'<details class="wxpanel".*?</details>\n', '', body, flags=re.S)
body = must(body, '<img src="__FACADE__"', '<img src="' + PHOTO + '" fetchpriority="high"')
# заглушки
body = re.sub(r'\s*<a class="fact" href="#reviews">.*?</a>', '', body, flags=re.S)
body = re.sub(r'<section class="sec" id="reviews".*?</section>\n\n', '', body, flags=re.S)
body = must(body, '<a href="#reviews">Отзывы</a>', '')
body = re.sub(r'\s*<a href="#reviews">.*?Отзывы гостей</a>', '', body, flags=re.S)
body = re.sub(r'\s*<div><span class="ic" aria-hidden="true">(?:(?!</div>).)*\[Ваш бонус\].*?</div>', '', body, count=1, flags=re.S)
body = must(body, 'Бронируя напрямую — <b>[ваш бонус]</b> и без комиссии агрегаторов', 'Бронируя напрямую — без комиссии агрегаторов')
body = must(body, ' — сауна ([цена]) и партия', ' — сауна и партия')
body = must(body, ' (за питомца [доплата])', '')
body = re.sub(r'\s*<div><span>[^<]*</span><span>\[[^\]]*\][^<]*</span></div>', '', body)
body = re.sub(r'<section class="sec" id="faq".*?</section>\n\n', '', body, count=1, flags=re.S)
body = re.sub(r'\s*<li data-ph>.*?</li>', '', body)
body = must(body, '\n      <a href="#">Реестр</a>', '')
assert '[' not in re.sub(r'<script.*?</script>', '', body, flags=re.S).replace('[open]', ''), re.findall(r'.{40}\[[^\]]*\].{20}', body)
body = '<div id="lg" class="nowx">' + body.strip() + '\n</div>'

# ---------- Скрипт ----------
assert js.lstrip().startswith('(function(){')
js = js.replace("(function(){\n", "(function(){\n  var LG = document.getElementById('lg'); document.documentElement.style.scrollBehavior = 'smooth';\n", 1)
js = must(js, "r = document.documentElement.style;", "r = LG.style;")
js = must(js, "var PREVIEW = true;", "var PREVIEW = false;")
js = must(js, "getComputedStyle(document.documentElement)", "getComputedStyle(LG)")
js = re.sub(r"    document\.getElementById\('wxMode'\).*?\n", '', js)
js = re.sub(r"    document\.querySelectorAll\('\[data-(?:k|ph)\]'\).*?\n", '', js)
js = re.sub(r"      document\.getElementById\('wxNote'\).*?\n", '', js)
js = must(js, "W.live = true; W.temp", "LG.classList.remove('nowx'); W.live = true; W.temp")
js = must(js, "    }).catch(function(){\n      W.live = false;", "    }).catch(function(){\n      if (W.live) return; LG.classList.add('nowx');\n      W.live = false;")
js = re.sub(r"  /\* Закрыть панель погоды.*?\n(?:  .*wxp.*\n)+", '', js)
js = re.sub(r"  /\* Панель предпросмотра погоды \*/\n(?:  .*\n){6}", '', js)
for bad in ('wxMode', 'wxNote', 'wxKinds', 'wxPanel', 'wxAuto', 'wxClose'):
    assert bad not in js, bad
assert 'wxPanel' not in body

out = ('<!-- Эко-отель «Легенда» · главная страница · блок T123. Весь код в одном блоке: при обновлении заменяйте его целиком. -->\n'
       + fonts + '\n<style>\n' + css + '</style>\n' + body + '\n<script>\n' + js + '</script>\n')
open(OUT, 'w', encoding='utf-8').write(out)
print(OUT, len(out.encode()), 'bytes;', PREVIEW, 'обновлён')
