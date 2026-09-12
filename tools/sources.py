#!/usr/bin/env python3
"""Сбор исходников чужих модов в ../original_mods для построчной сверки.

    python3 tools/sources.py           # собрать из того, что есть на диске
    python3 tools/sources.py --links   # открыть в браузере страницу загрузок
    python3 tools/sources.py --list    # только отчёт, ничего не менять

Берётся ТОЛЬКО папка locale/, и только языки en и ru: графика и звук чужих
модов нам не нужны, а весят они сотни мегабайт. Папка ../original_mods лежит
вне репозитория и в git не попадает — это тексты авторов соответствующих
модов, а не наши.

Архивы ищутся в двух местах: в папке модов Factorio (то, что установлено
в игре) и в «Загрузках» (то, что скачано браузером).

Скачивать архивы из скрипта нельзя: страницы загрузки портала стоят за
Cloudflare и отдают 403 любому клиенту, кроме браузера и самой игры.
Поэтому --links: скрипт складывает прямые ссылки на последние версии
недостающих модов в dist/download-mods.html и открывает её в браузере,
где вы уже залогинены. Скачанные zip достаточно оставить в «Загрузках» —
следующий запуск без ключей подхватит их сам.
"""
import argparse
import glob
import io
import json
import os
import re
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MOD = os.path.join(ROOT, 'mod')
DIST = os.path.join(ROOT, 'dist')
OUT = os.path.abspath(os.path.join(ROOT, os.pardir, 'original_mods'))

APPDATA = os.environ.get('APPDATA') or os.path.expanduser('~')
MODS_DIR = os.path.join(APPDATA, 'Factorio', 'mods')
DOWNLOADS = os.path.join(os.path.expanduser('~'), 'Downloads')

API = 'https://mods.factorio.com/api/mods/%s'
PORTAL = 'https://mods.factorio.com'
LANGS = ('en', 'ru')


def dependencies():
    info = json.load(io.open(os.path.join(MOD, 'info.json'), encoding='utf-8'))
    return [d.lstrip('?!~()').strip().split(' ')[0] for d in info['dependencies']]


def collected():
    """Что уже лежит в original_mods: имя мода -> версия."""
    out = {}
    if not os.path.isdir(OUT):
        return out
    for name in os.listdir(OUT):
        m = re.match(r'^(.*)_(\d+\.\d+\.\d+)$', name)
        if m:
            out[m.group(1)] = m.group(2)
    return out


def extract(zip_path, stem):
    """Кладёт locale/{en,ru} из архива в original_mods/<stem>/."""
    try:
        zf = zipfile.ZipFile(zip_path)
    except Exception:
        return 0
    written = 0
    for name in zf.namelist():
        if '/locale/' not in name or not name.endswith('.cfg'):
            continue
        parts = name.split('/')
        if parts[parts.index('locale') + 1] not in LANGS:
            continue
        dest = os.path.join(OUT, stem, *parts[parts.index('locale'):])
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, 'wb') as handle:
            handle.write(zf.read(name))
        written += 1
    return written


def harvest():
    """Проходит по обеим папкам с архивами. -> (модов, файлов, откуда)."""
    mods = files = 0
    where = []
    for folder in (MODS_DIR, DOWNLOADS):
        if not os.path.isdir(folder):
            continue
        here = 0
        for archive in sorted(glob.glob(os.path.join(folder, '*.zip'))):
            stem = os.path.splitext(os.path.basename(archive))[0]
            n = extract(archive, stem)
            if n:
                mods += 1
                files += n
                here += 1
        if here:
            where.append('%s — %d' % (folder, here))
    return mods, files, where


def latest(names):
    """Последние версии недостающих модов. Метаданные портал отдаёт открыто."""
    import urllib.parse
    import urllib.request
    rows = []
    for name in names:
        try:
            meta = json.load(urllib.request.urlopen(API % urllib.parse.quote(name)))
            rel = meta['releases'][-1]
            rows.append((meta.get('title') or name, rel['version'],
                         PORTAL + rel['download_url'], rel['file_name']))
        except Exception:
            rows.append((name, '?', PORTAL + '/mod/' + name, ''))
    return rows


HTML_HEAD = """<!doctype html><meta charset="utf-8">
<title>Моды для сверки</title>
<style>
 body{font:15px/1.6 system-ui,sans-serif;max-width:640px;margin:40px auto;padding:0 16px}
 h1{font-size:20px} ol{padding-left:22px} li{margin:12px 0}
 a{font-weight:600} .v{color:#777;font-size:13px;margin-left:6px}
 .f{color:#999;font-size:12px} button{font:inherit;padding:8px 14px;cursor:pointer}
 p.note{color:#555;font-size:13px}
</style>
"""

HTML_SCRIPT = """<script>
function go(){
  var links = document.querySelectorAll('ol a'), i = 0;
  (function next(){
    if (i >= links.length) return;
    window.open(links[i++].href, '_blank');
    setTimeout(next, 1200);
  })();
}
</script>
"""


def make_page(rows):
    items = []
    for title, version, url, file_name in rows:
        items.append('<li><a href="%s">%s</a><span class="v">%s</span>'
                     '<div class="f">%s</div></li>'
                     % (url, title, version, file_name))
    body = (HTML_HEAD
            + '<h1>Моды, по которым нет исходников — %d</h1>\n' % len(rows)
            + '<p class="note">Вы залогинены на портале, поэтому ссылки скачаются '
              'напрямую. Браузер, скорее всего, спросит разрешение на несколько '
              'файлов сразу — разрешите. Сохраняйте в «Загрузки», скрипт заберёт '
              'их оттуда.</p>\n'
            + '<p><button onclick="go()">Скачать все по очереди</button></p>\n'
            + '<ol>\n' + '\n'.join(items) + '\n</ol>\n'
            + HTML_SCRIPT)
    os.makedirs(DIST, exist_ok=True)
    path = os.path.join(DIST, 'download-mods.html')
    io.open(path, 'w', encoding='utf-8', newline='\n').write(body)
    return path


def main(argv):
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument('--links', action='store_true',
                        help='собрать и открыть страницу со ссылками на загрузку')
    parser.add_argument('--list', action='store_true',
                        help='только отчёт, ничего не менять')
    args = parser.parse_args(argv)

    if not args.list:
        mods, files, where = harvest()
        print('Собрано: %d модов, %d файлов locale.' % (mods, files))
        for line in where:
            print('   %s' % line)

    have = collected()
    deps = dependencies()
    missing = [d for d in deps if d not in have]

    print()
    print('Зависимостей: %d | исходники есть: %d | не хватает: %d'
          % (len(deps), len(deps) - len(missing), len(missing)))
    for name in missing:
        print('   нет исходника: %s' % name)

    if not missing:
        return 0

    if args.links:
        path = make_page(latest(missing))
        print()
        print('Страница со ссылками: %s' % path)
        try:
            os.startfile(path)
            print('Открыта в браузере.')
        except AttributeError:
            import webbrowser
            webbrowser.open('file://' + path)
    else:
        print()
        print('Открыть страницу загрузок: python3 tools/sources.py --links')
        print('Либо поставить недостающие через игру: Моды -> Установить.')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
