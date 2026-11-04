"""Упаковать site/ в архивы до ~9 МБ — для загрузки через файловый менеджер Timeweb (там их можно распаковать).
Запуск из корня: python tools/site-zip.py <папка_для_архивов>
Архив 1 — страницы, служебные файлы, обложка, значки; остальные — фото номеров (img/r/)."""
import os, sys, zipfile

out = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else 'site-zip')
os.makedirs(out, exist_ok=True)
os.chdir('site')
files = sorted(os.path.relpath(os.path.join(d, f), '.').replace(os.sep, '/') for d, _, fs in os.walk('.') for f in fs)
groups, cur, size = [[f for f in files if not f.startswith('img/r/')]], [], 0
for f in (f for f in files if f.startswith('img/r/')):
    s = os.path.getsize(f)
    if cur and size + s > 8_500_000:
        groups.append(cur); cur, size = [], 0
    cur.append(f); size += s
groups.append(cur)
for i, g in enumerate(groups, 1):
    z = os.path.join(out, f'legenda-{i}.zip')
    with zipfile.ZipFile(z, 'w', zipfile.ZIP_DEFLATED) as zf:
        for f in g:
            zf.write(f, f)
    print(z, len(g), 'файлов,', os.path.getsize(z) // 1024, 'КБ')
