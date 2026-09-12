#!/usr/bin/env python3
"""Сбор исходников чужих модов в ../original_mods для построчной сверки.

    python3 tools/sources.py              # из установленных модов + отчёт
    python3 tools/sources.py --download   # доскачать недостающие с портала
    python3 tools/sources.py --list       # только отчёт, ничего не трогать

Берётся ТОЛЬКО папка locale/, и только языки en и ru: графика и звук чужих
модов нам не нужны, а весят они сотни мегабайт. Папка ../original_mods лежит
вне репозитория и в git не попадает — это тексты авторов соответствующих
модов, а не наши.

Про --download. Портал отдаёт архивы только авторизованным: нужны
service-username и service-token из player-data.json Factorio. Скрипт читает
их сам и никуда не печатает. Если файла нет или в нём нет токена — запустите
игру и войдите в аккаунт, токен появится. Скачивать можно и вручную через
саму игру: Моды -> Установить, тогда хватит запуска без --download.
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
OUT = os.path.abspath(os.path.join(ROOT, os.pardir, 'original_mods'))

APPDATA = os.environ.get('APPDATA') or os.path.expanduser('~')
FACTORIO = os.path.join(APPDATA, 'Factorio')
MODS_DIR = os.path.join(FACTORIO, 'mods')
PLAYER_DATA = os.path.join(FACTORIO, 'player-data.json')

API = 'https://mods.factorio.com/api/mods/%s'
LANGS = ('en', 'ru')


def dependencies():
    info = json.load(io.open(os.path.join(MOD, 'info.json'), encoding='utf-8'))
    return [d.lstrip('?!~()').strip().split(' ')[0] for d in info['dependencies']]


def collected():
    """Что уже лежит в original_mods: имя мода -> версия."""
    out = {}
    if not os.path.isdir(OUT):
        return out
    for d in os.listdir(OUT):
        m = re.match(r'^(.*)_(\d+\.\d+\.\d+)$', d)
        if m:
            out[m.group(1)] = m.group(2)
    return out


def extract(zip_path, stem):
    """Кладёт locale/{en,ru} из архива в original_mods/<stem>/."""
    try:
        zf = zipfile.ZipFile(zip_path)
    except Exception as exc:
        print('  не читается %s: %s' % (os.path.basename(zip_path), exc))
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
        with open(dest, 'wb') as f:
            f.write(zf.read(name))
        written += 1
    return written


def from_installed():
    total_mods = total_files = 0
    for z in sorted(glob.glob(os.path.join(MODS_DIR, '*.zip'))):
        stem = os.path.splitext(os.path.basename(z))[0]
        n = extract(z, stem)
        if n:
            total_mods += 1
            total_files += n
    return total_mods, total_files


def credentials():
    """service-username и service-token из player-data.json. Не печатаются."""
    if not os.path.exists(PLAYER_DATA):
        return None, None
    try:
        data = json.load(io.open(PLAYER_DATA, encoding='utf-8'))
    except Exception:
        return None, None
    return data.get('service-username'), data.get('service-token')


def download(names):
    import urllib.parse
    import urllib.request

    user, token = credentials()
    if not user or not token:
        print('\nВ %s нет service-token — портал архивы не отдаст.' % PLAYER_DATA)
        print('Запустите Factorio и войдите в аккаунт, либо поставьте моды '
              'через саму игру (Моды -> Установить).')
        return 1

    for name in names:
        try:
            meta = json.load(urllib.request.urlopen(API % urllib.parse.quote(name)))
            rel = meta['releases'][-1]
        except Exception as exc:
            print('  %-30s портал не ответил: %s' % (name, exc))
            continue
        stem = os.path.splitext(rel['file_name'])[0]
        url = ('https://mods.factorio.com' + rel['download_url'] + '?' +
               urllib.parse.urlencode({'username': user, 'token': token}))
        tmp = os.path.join(OUT, stem + '.part')
        os.makedirs(OUT, exist_ok=True)
        try:
            with urllib.request.urlopen(url) as resp, open(tmp, 'wb') as f:
                f.write(resp.read())
        except Exception as exc:
            print('  %-30s не скачался: %s' % (name, exc))
            continue
        n = extract(tmp, stem)
        os.remove(tmp)
        print('  %-30s %-10s locale-файлов: %d' % (name, rel['version'], n))
    return 0


def main(argv):
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument('--download', action='store_true',
                        help='доскачать недостающие моды с портала')
    parser.add_argument('--list', action='store_true',
                        help='только отчёт, ничего не менять')
    args = parser.parse_args(argv)

    if not args.list:
        mods, files = from_installed()
        print('Из установленных модов: %d модов, %d файлов locale.' % (mods, files))

    have = collected()
    missing = [d for d in dependencies() if d not in have]

    print('\nВ пакете зависимостей: %d | исходники есть: %d | не хватает: %d'
          % (len(dependencies()), len(dependencies()) - len(missing), len(missing)))
    for d in missing:
        print('   нет исходника: %s' % d)

    if missing and args.download:
        print('\nСкачиваю с портала:')
        return download(missing)
    if missing and not args.list:
        print('\nДоскачать: python3 tools/sources.py --download')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
