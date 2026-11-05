"""Сборка сайта hotellegenda.ru → папка site/ (её содержимое загружается на хостинг Timeweb, в tilda/public_html).
Запуск из корня репозитория:  python tools/build.py

Из чего собирается:
  src/index.html     — страница целиком (разметка, стили, скрипт, разметка для поисковиков). Все правки — здесь.
  src/facade.jpg     — фото обложки; src/depth.jpg — карта глубины к нему (tools/sky-mask.py)
  src/rooms/*.jpg    — фото номеров (имена — в PHOTOS в скрипте страницы)
  src/static/        — файлы как есть: значки, картинка для соцсетей
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
def doc(title, inner):
    return f'''<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)}</title>
<link rel="icon" href="/favicon.ico" sizes="32x32">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Golos+Text:wght@400;600&family=Lora:wght@600&display=swap">
<style>
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
save(f'{OUT}/404.html', doc('Страница не найдена — эко-отель «Легенда»',
     '<h1>Такой страницы нет</h1>\n<p>Возможно, ссылка устарела. Всё о номерах, ценах и бронировании — <a href="/">на главной</a>.</p>'))

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
</IfModule>
''')
total = sum(os.path.getsize(os.path.join(d, f)) for d, _, fs in os.walk(OUT) for f in fs)
print(f'{OUT}/ собран: страница {os.path.getsize(OUT + "/index.html") // 1024} КБ, {len(photos)} фото номеров, всего {total // 1024} КБ')
