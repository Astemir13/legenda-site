"""Сборка сайта hotellegenda.ru → папка site/ (её содержимое загружается на хостинг Timeweb, в tilda/public_html).
Запуск из корня репозитория:  python tools/build.py

Из чего собирается:
  src/index.html     — страница целиком (разметка, стили, скрипт, разметка для поисковиков). Все правки — здесь.
  src/facade.jpg     — фото обложки; src/depth.jpg — карта глубины к нему (tools/sky-mask.py)
  src/rooms/*.jpg    — фото номеров (имена — в PHOTOS в скрипте страницы)
  src/static/        — файлы как есть: значки, картинка для соцсетей, шрифты (fonts/)
  src/privacy.txt    — текст политики обработки персональных данных

Что делает:
  — убирает из страницы разделы с заглушками в [скобках] (отзывы, вопросы), пока их нечем заполнить;
  — сжимает скрипт (без комментариев и отступов) и разметку для поисковиков;
  — обложку и фото номеров переводит в webp нужных размеров;
  — делает политику (/privacypolicy/), страницу 404, robots.txt, sitemap.xml, .htaccess."""
import datetime, html, json, os, re, shutil
from PIL import Image

OUT = 'site'
DOMAIN = 'https://hotellegenda.ru'


def must(s, a, b, n=1):
    c = s.count(a)
    assert c == n, (a[:80], c)
    return s.replace(a, b)


def save(path, text):
    os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
    open(path, 'w', encoding='utf-8', newline='\n').write(text)


def compact_js(js):
    """Без комментариев и отступов — быстрее загрузка (исходник остаётся читаемым)."""
    js = re.sub(r'^[ \t]*/\*.*?\*/[ \t]*\n', '', js, flags=re.M | re.S)
    js = re.sub(r'^[ \t]+', '', js, flags=re.M)  # в скрипте нет многострочных строк
    assert not re.search(r"""['"][^'"\n]*/\*""", js), 'в строке скрипта есть /* — вырезание комментариев её испортит'
    return re.sub(r'[ \t]*/\*.*?\*/', '', js, flags=re.S)


# ---------- страница ----------
page = open('src/index.html', encoding='utf-8').read()
# разделы и строки с заглушками — до тех пор, пока владелец не даст настоящий текст
page = re.sub(r'<section class="sec" id="reviews".*?</section>\n\n', '', page, flags=re.S)
page = must(page, '<a href="#reviews">Отзывы</a>', '')
page = re.sub(r'\s*<a href="#reviews">.*?Отзывы гостей</a>', '', page, flags=re.S)
page = must(page, ' (за питомца [доплата])', '')
page = re.sub(r'\s*<div><span>[^<]*</span><span>\[[^\]]*\][^<]*</span></div>', '', page)
page = re.sub(r'<section class="sec" id="faq".*?</section>\n\n', '', page, count=1, flags=re.S)
page = re.sub(r'\s*<li data-ph>.*?</li>', '', page)
visible = re.sub(r'<(script|style)\b.*?</\1>', '', page[page.index('<body>'):], flags=re.S)
assert '[' not in visible.replace('[open]', ''), re.findall(r'.{40}\[[^\]]*\].{20}', visible)
# скрипт и разметка для поисковиков — компактно
main_js = re.search(r'<script>\n(\(function\(\)\{.*?)</script>', page, re.S)
page = page.replace(main_js.group(1), compact_js(main_js.group(1)))
ld = re.search(r'(<script type="application/ld\+json">)(.*?)(</script>)', page, re.S)
page = page.replace(ld.group(0), ld.group(1) + json.dumps(json.loads(ld.group(2)), ensure_ascii=False, separators=(',', ':')) + ld.group(3))
page = re.sub(r'<style>\n/\*.*?\*/\n', '<style>\n', page, count=1, flags=re.S)  # служебный комментарий в начале стилей

# очищаем содержимое site/, а не саму папку — её может держать открытой локальный сервер для проверки
os.makedirs(OUT, exist_ok=True)
for f in os.listdir(OUT):
    q = os.path.join(OUT, f); shutil.rmtree(q) if os.path.isdir(q) else os.remove(q)
save(f'{OUT}/index.html', page)

# ---------- картинки ----------
os.makedirs(f'{OUT}/img/r')
im = Image.open('src/facade.jpg').convert('RGB')
im.save(f'{OUT}/img/facade.webp', 'WEBP', quality=78, method=6)
im.save(f'{OUT}/img/facade.jpg', 'JPEG', quality=85, optimize=True, progressive=True)  # для соцсетей и поисковиков
shutil.copy('src/depth.jpg', f'{OUT}/img/depth.jpg')
photos = re.findall(r"'([a-z0-9]+-\d+)'", re.search(r'var PHOTOS = \{(.*?)\};', page, re.S).group(1))
for n in photos:
    ph = Image.open(f'src/rooms/{n}.jpg').convert('RGB')
    for w, name in ((1800, n), (760, n + '-760'), (160, n + '-160')):
        s = ph.copy(); s.thumbnail((w, w * 4)); s.save(f'{OUT}/img/r/{name}.webp', 'WEBP', quality=80, method=6)
shutil.copytree('src/static', OUT, dirs_exist_ok=True)

# ---------- политика и 404 ----------
e = html.escape
# шрифты — те же, что на главной (свои файлы в fonts/), адреса от корня: 404 открывается по любому адресу
FONTS = '\n'.join(l.replace('src:url(fonts/', 'src:url(/fonts/') for l in re.findall(r"@font-face\{font-family:'(?:Golos Text|Lora)'[^\n]*", page))
assert FONTS.count('@font-face') == 6, 'шрифты для политики и 404 не найдены в странице'
def doc(title, inner):
    return f'''<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)}</title>
<link rel="icon" href="/favicon.ico" sizes="32x32">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<style>
{FONTS}
body{{margin:0;background:#F4F7F8;color:#13202A;font:16px/1.6 'Golos Text',system-ui,sans-serif}}
main{{max-width:760px;margin:0 auto;padding:40px 20px 64px}}
a{{color:#1F5C4A}}
h1,h2{{font-family:'Lora',Georgia,serif;font-weight:600;line-height:1.2}}
h1{{font-size:32px;margin:24px 0 16px}}
h2{{font-size:21px;margin:32px 0 8px}}
p{{margin:0 0 10px}}
.back{{display:inline-block;margin-bottom:8px;font-weight:600;text-decoration:none}}
</style>
</head>
<body>
<main>
<a class="back" href="/">← Эко-отель «Легенда»</a>
{inner}
</main>
</body>
</html>
'''
paras = []
for line in open('src/privacy.txt', encoding='utf-8').read().strip().split('\n'):
    line = line.strip()
    if not line:
        continue
    if re.match(r'^\d+\. .{0,90}$', line) and not line.endswith((';', '.')):
        paras.append(f'<h2>{e(line)}</h2>')
    else:
        paras.append(f'<p>{e(line.lstrip("-"))}</p>')
save(f'{OUT}/privacypolicy/index.html', doc('Политика обработки персональных данных — эко-отель «Легенда»',
     '<h1>Политика обработки персональных данных</h1>\n' + '\n'.join(paras)))
# 404: фото фасада под тёмной вуалью, по центру — логотип, крупное «404», «Страница не найдена» и кнопка на главную
MARK = re.search(r'<svg class="mk" viewBox="[^"]+" aria-hidden="true">.*?</svg>', page).group(0)
save(f'{OUT}/404.html', f'''<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="robots" content="noindex">
<meta name="theme-color" content="#0F2A23">
<title>Страница не найдена — эко-отель «Легенда»</title>
<link rel="icon" href="/favicon.ico" sizes="32x32">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="preload" as="image" href="/img/facade.webp">
<style>
{FONTS}
*{{box-sizing:border-box}}
html,body{{height:100%}}
body{{margin:0;background:#0F2A23;color:#fff;font:16px/1.55 'Golos Text',system-ui,sans-serif;-webkit-font-smoothing:antialiased}}
.bg{{position:fixed;inset:0;background:#0F2A23 url(/img/facade.webp) 50% 55%/cover no-repeat}}
.bg::after{{content:"";position:absolute;inset:0;background:radial-gradient(120% 90% at 50% 45%,rgba(10,30,25,.55),rgba(8,22,18,.88)),linear-gradient(180deg,rgba(8,22,18,.35),rgba(8,22,18,.75))}}
main{{position:relative;min-height:100%;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:0;padding:48px max(20px,env(safe-area-inset-left)) 40px;text-align:center}}
.brand{{display:flex;flex-direction:column;align-items:center;gap:10px;color:#fff;text-decoration:none}}
.brand svg{{width:92px;height:auto;opacity:.95}}
.brand b{{font:600 15px/1 'Golos Text',sans-serif;letter-spacing:.32em;margin-right:-.32em}}
.brand small{{font-size:12.5px;letter-spacing:.06em;opacity:.7}}
.code{{margin:clamp(28px,6vh,52px) 0 0;font:600 clamp(96px,22vw,168px)/.9 'Lora',Georgia,serif;letter-spacing:-.02em;color:transparent;-webkit-text-stroke:1.5px rgba(255,255,255,.75);text-shadow:0 10px 40px rgba(0,0,0,.25)}}
h1{{margin:18px 0 0;font:600 clamp(26px,4.4vw,36px)/1.2 'Lora',Georgia,serif}}
p{{max-width:440px;margin:12px 0 0;text-wrap:balance;color:rgba(232,240,236,.82);font-size:16.5px}}
.btn{{display:inline-flex;align-items:center;gap:10px;margin-top:30px;min-height:52px;padding:0 28px;border-radius:999px;background:#1F5C4A;color:#fff;font-weight:600;font-size:16px;text-decoration:none;box-shadow:inset 0 1px 0 rgba(255,255,255,.18),0 10px 28px rgba(0,0,0,.3);transition:background .2s,transform .2s}}
.btn:hover{{background:#24705A;transform:translateY(-1px)}}
.btn svg{{width:18px;height:18px}}
footer{{position:relative;margin-top:auto;padding-top:40px;font-size:13px;color:rgba(232,240,236,.55)}}
footer a{{color:inherit}}
</style>
</head>
<body>
<div class="bg" aria-hidden="true"></div>
<main>
<a class="brand" href="/" aria-label="Эко-отель «Легенда» — на главную">{MARK}<b>ЛЕГЕНДА</b><small>Эко-отель · Терскол</small></a>
<div class="code" aria-hidden="true">404</div>
<h1>Страница не найдена</h1>
<p>Возможно, ссылка устарела или в адресе опечатка. Номера, цены и бронирование — на главной странице.</p>
<a class="btn" href="/"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 11l9-7 9 7"/><path d="M5 10v10h14V10"/></svg>На главную</a>
<footer>с. Терскол, ул. Чегет, 5А · <a href="tel:+79993000088">+7 999 300-00-88</a></footer>
</main>
</body>
</html>
''')

# ---------- служебные файлы ----------
today = datetime.date.today().isoformat()
save(f'{OUT}/robots.txt', f'User-agent: *\nAllow: /\n\nSitemap: {DOMAIN}/sitemap.xml\n')
save(f'{OUT}/sitemap.xml', f'''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>{DOMAIN}/</loc><lastmod>{today}</lastmod></url>
  <url><loc>{DOMAIN}/privacypolicy/</loc><lastmod>{today}</lastmod></url>
</urlset>
''')
save(f'{OUT}/.htaccess', r'''AddDefaultCharset utf-8
AddType font/woff2 .woff2
Options -Indexes
DirectoryIndex index.html
ErrorDocument 404 /404.html

<IfModule mod_rewrite.c>
RewriteEngine On
# www.hotellegenda.ru -> hotellegenda.ru
RewriteCond %{HTTP_HOST} ^www\.(.+)$ [NC]
RewriteRule ^ https://%1%{REQUEST_URI} [L,R=301]
# http -> https: включается в панели Timeweb («SSL» → «Перенаправлять на HTTPS») — без петли переадресаций
# адреса прежнего сайта (на Тильде), которые знают поисковики, — на главную
RewriteRule ^new/?$ / [L,R=301]
RewriteRule ^page59460067\.html$ / [L,R=301]
RewriteRule ^page59652773\.html$ / [L,R=301]
RewriteCond %{THE_REQUEST} \s/index\.html[\s?]
RewriteRule ^index\.html$ / [L,R=301]
RewriteRule ^privacypolicy$ /privacypolicy/ [L,R=301]
</IfModule>

<IfModule mod_deflate.c>
AddOutputFilterByType DEFLATE text/html text/css text/plain text/xml application/javascript application/json image/svg+xml
</IfModule>

<IfModule mod_expires.c>
ExpiresActive On
ExpiresDefault "access plus 1 hour"
ExpiresByType text/html "access plus 0 seconds"
ExpiresByType image/webp "access plus 30 days"
ExpiresByType image/jpeg "access plus 30 days"
ExpiresByType image/png "access plus 30 days"
ExpiresByType image/svg+xml "access plus 30 days"
ExpiresByType image/x-icon "access plus 30 days"
ExpiresByType font/woff2 "access plus 1 year"
</IfModule>
''')
total = sum(os.path.getsize(os.path.join(d, f)) for d, _, fs in os.walk(OUT) for f in fs)
print(f'{OUT}/ собран: страница {os.path.getsize(OUT + "/index.html") // 1024} КБ, {len(photos)} фото номеров, всего {total // 1024} КБ')
