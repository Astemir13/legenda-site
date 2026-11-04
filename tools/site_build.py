"""Сайт для своего хостинга (Timeweb, Apache) — папка site/. Вызывается из tools/build.py.

Что внутри:
  index.html            — главная: та же страница, что на Тильде, но целиком, без лимитов и без панели «Погода»;
                          мета-теги для поиска и соцсетей, Яндекс Метрика (тот же счётчик), разметка Hotel
  privacypolicy/        — политика обработки персональных данных (текст — src/privacy.txt, как был на Тильде)
  404.html              — страница «не найдено»
  img/facade.webp|.jpg  — обложка (webp — на странице, jpg — для соцсетей и поисковиков)
  img/og.jpg            — картинка для превью ссылки в соцсетях
  img/r/                — фото номеров: для просмотра (до 1800 px) и уменьшенные (-760, -160), всё в webp
  favicon.*             — значки сайта
  robots.txt, sitemap.xml, .htaccess (переадресации, кэш, сжатие)
Фото номеров и значки один раз скачиваются из Тильды в .cache/ — сайт от Тильды не зависит.
Загрузка на хостинг: всё содержимое site/ — в папку public_html сайта."""
import datetime, html, io, os, re, shutil, urllib.request
from PIL import Image

OUT = 'site'
CACHE = '.cache'
DOMAIN = 'https://hotellegenda.ru'
METRIKA = 104834110
TITLE = 'Эко-отель «Легенда» в Терсколе — гостиница в Приэльбрусье у Чегета и Эльбруса'
DESCR = ('Дом из сруба на 17 номеров и отдельный коттедж в Терсколе, Приэльбрусье: 500 м до Чегета, 5 км до Азау. '
         'Свой ресторан, вид на горы. Напрямую — завтрак включён, без комиссии.')
# значки и картинка для соцсетей — те, что сейчас стоят на Тильде
REMOTE = {
    'favicon.ico': 'https://static.tildacdn.com/tild3133-3564-4263-b761-653163333566/favicon.ico',
    'favicon-dark.ico': 'https://static.tildacdn.com/tild6466-3662-4033-a663-373336333666/favicon.ico',
    'favicon.svg': 'https://static.tildacdn.com/tild3336-3930-4435-a263-643561383337/favicon.svg',
    'favicon-512.png': 'https://static.tildacdn.com/tild3234-6231-4739-b038-303963633063/favicon-512.png',
    'img/og.jpg': 'https://static.tildacdn.com/tild3961-3231-4661-b135-323063343839/og_legenda_1200x630.jpg',
}


def fetch(url, path):
    """Скачать файл один раз в кэш; дальше берётся из кэша."""
    if not os.path.exists(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        req = urllib.request.Request(url, headers={'User-Agent': 'legenda-site-build'})
        with urllib.request.urlopen(req, timeout=60) as r, open(path + '.part', 'wb') as f:
            f.write(r.read())
        os.replace(path + '.part', path)
    return path


def photo_name(p):
    """Имя файла фото номера — та же формула, что в phUrl() на странице."""
    return re.sub(r'\.\w+$', '', re.sub(r'[^A-Za-z0-9_.]+', '-', p))


def save(path, text):
    os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
    open(path, 'w', encoding='utf-8', newline='\n').write(text)


def build(fonts, css, body, js, ld):
    # очищаем содержимое, а не саму папку — её может держать открытой локальный сервер для проверки
    os.makedirs(OUT, exist_ok=True)
    for f in os.listdir(OUT):
        q = os.path.join(OUT, f); shutil.rmtree(q) if os.path.isdir(q) else os.remove(q)
    os.makedirs(OUT + '/img/r')

    # --- картинки: обложка и фото номеров ---
    im = Image.open('src/facade.jpg').convert('RGB')
    im.save(OUT + '/img/facade.webp', 'WEBP', quality=78, method=6)
    im.save(OUT + '/img/facade.jpg', 'JPEG', quality=85, optimize=True, progressive=True)
    photos = sorted(set(re.findall(r"'(tild[^']+\.(?:jpe?g|png|webp))'", js)))
    for p in photos:
        src = fetch('https://static.tildacdn.com/' + p, os.path.join(CACHE, 'photos', photo_name(p) + os.path.splitext(p)[1]))
        ph = Image.open(src).convert('RGB'); n = photo_name(p)
        big = ph.copy(); big.thumbnail((1800, 1800)); big.save(f'{OUT}/img/r/{n}.webp', 'WEBP', quality=80, method=6)
        for w in (760, 160):
            s = ph.copy(); s.thumbnail((w, w * 4)); s.save(f'{OUT}/img/r/{n}-{w}.webp', 'WEBP', quality=80, method=6)
    for name, url in REMOTE.items():
        shutil.copy(fetch(url, os.path.join(CACHE, 'remote', name.replace('/', '_'))), os.path.join(OUT, name))

    # --- скрипт: фото номеров со своего хостинга ---
    local = (r"function phUrl(p, w){ var f = p.replace(/[^A-Za-z0-9_.]+/g, '-').replace(/\.\w+$/, ''); "
             r"return '/img/r/' + f + (w ? '-' + (w > 300 ? 760 : 160) : '') + '.webp'; }" + '\n')
    js, n = re.subn(r"function phUrl\(p, w\)\{.*?\}\n", lambda m: local, js, count=1, flags=re.S)
    assert n == 1, 'phUrl не найдена'
    assert 'tildacdn' not in js.replace("'tild", "'"), 'в скрипте остались ссылки на Тильду'

    # --- страница ---
    # скрипт ставит класс режима обложки (hc) на обёртку #lg — стили, рассчитанные на :root.hc, переводим на неё
    css = css.replace(':root.hc', '#lg.hc').replace(':root.nowx', '#lg.nowx')
    body = body.replace('<img src="__FACADE__"', '<img src="/img/facade.webp" fetchpriority="high"', 1)
    ld = ld.replace('https://static.tildacdn.com/tila3835-3766-4537-b437-653539313566/facade.jpg', DOMAIN + '/img/facade.jpg')
    e = html.escape
    head = f'''<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{e(TITLE)}</title>
<meta name="description" content="{e(DESCR)}">
<link rel="canonical" href="{DOMAIN}/">
<meta name="theme-color" content="#1F5C4A">
<meta property="og:type" content="website">
<meta property="og:locale" content="ru_RU">
<meta property="og:site_name" content="Эко-отель «Легенда»">
<meta property="og:url" content="{DOMAIN}/">
<meta property="og:title" content="{e(TITLE)}">
<meta property="og:description" content="{e(DESCR)}">
<meta property="og:image" content="{DOMAIN}/img/og.jpg">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="/favicon.ico" sizes="32x32" media="(prefers-color-scheme: light)">
<link rel="icon" href="/favicon-dark.ico" sizes="32x32" media="(prefers-color-scheme: dark)">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="/favicon-512.png">
<link rel="preload" as="image" href="/img/facade.webp" fetchpriority="high">
{fonts}
<style>
{css}</style>
{ld}
</head>
<body>
'''
    metrika = f'''<!-- Яндекс Метрика -->
<script>(function(m,e,t,r,i,k,a){{m[i]=m[i]||function(){{(m[i].a=m[i].a||[]).push(arguments)}};m[i].l=1*new Date();k=e.createElement(t),a=e.getElementsByTagName(t)[0],k.async=1,k.src=r,a.parentNode.insertBefore(k,a)}})(window,document,"script","https://mc.yandex.ru/metrika/tag.js","ym");
ym({METRIKA},"init",{{clickmap:true,trackLinks:true,accurateTrackBounce:true,webvisor:true}});</script>
<noscript><div><img src="https://mc.yandex.ru/watch/{METRIKA}" style="position:absolute;left:-9999px" alt=""></div></noscript>
'''
    save(OUT + '/index.html', head + body + '\n<script>\n' + js + '</script>\n' + metrika + '</body>\n</html>\n')

    # --- политика конфиденциальности ---
    paras = []
    for line in open('src/privacy.txt', encoding='utf-8').read().strip().split('\n'):
        line = line.strip()
        if not line:
            continue
        if re.match(r'^\d+\. .{0,90}$', line) and not line.endswith((';', '.')):
            paras.append(f'<h2>{e(line)}</h2>')
        else:
            paras.append(f'<p>{e(line.lstrip("-"))}</p>')
    page = lambda title, inner: f'''<!doctype html>
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
    save(OUT + '/privacypolicy/index.html', page('Политика обработки персональных данных — эко-отель «Легенда»',
         '<h1>Политика обработки персональных данных</h1>\n' + '\n'.join(paras)))
    save(OUT + '/404.html', page('Страница не найдена — эко-отель «Легенда»',
         '<h1>Такой страницы нет</h1>\n<p>Возможно, ссылка устарела. Всё о номерах, ценах и бронировании — <a href="/">на главной</a>.</p>'))

    # --- служебные файлы ---
    today = datetime.date.today().isoformat()
    save(OUT + '/robots.txt', f'User-agent: *\nAllow: /\n\nSitemap: {DOMAIN}/sitemap.xml\n')
    save(OUT + '/sitemap.xml', f'''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>{DOMAIN}/</loc><lastmod>{today}</lastmod></url>
  <url><loc>{DOMAIN}/privacypolicy/</loc><lastmod>{today}</lastmod></url>
</urlset>
''')
    save(OUT + '/.htaccess', '''AddDefaultCharset utf-8
Options -Indexes
DirectoryIndex index.html
ErrorDocument 404 /404.html

<IfModule mod_rewrite.c>
RewriteEngine On
# www.hotellegenda.ru -> hotellegenda.ru
RewriteCond %{HTTP_HOST} ^www\\.(.+)$ [NC]
RewriteRule ^ https://%1%{REQUEST_URI} [L,R=301]
# http -> https: включается в панели Timeweb («SSL» → «Перенаправлять на HTTPS») —
# там это делается на уровне сервера и не даёт петли переадресаций
# старые адреса с Тильды — на главную
RewriteRule ^new/?$ / [L,R=301]
RewriteRule ^page59460067\\.html$ / [L,R=301]
RewriteRule ^page59652773\\.html$ / [L,R=301]
RewriteCond %{THE_REQUEST} \\s/index\\.html[\\s?]
RewriteRule ^index\\.html$ / [L,R=301]
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
    print(f'{OUT}/ собран: {len(photos)} фото номеров, всего {total // 1024} КБ')
