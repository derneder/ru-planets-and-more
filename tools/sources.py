#!/usr/bin/env python3
"""Сбор исходников чужих модов в ../original_mods для построчной сверки.

    python3 tools/sources.py          # собрать из установленных модов + отчёт
    python3 tools/sources.py --list   # только отчёт, ничего не трогать

Берётся ТОЛЬКО папка locale/, и только языки en и ru: графика и звук чужих
модов нам не нужны, а весят они сотни мегабайт. Папка ../original_mods лежит
вне репозитория и в git не попадает — это тексты авторов соответствующих
модов, а не наши.

Скачивать архивы с портала скриптом НЕЛЬЗЯ: страницы загрузки стоят за
Cloudflare, который отдаёт 403 (код 1010) любому клиенту, кроме браузера
и самой игры. Дело не в авторизации — запрос не доходит до портала.

Поэтому недостающие моды ставятся через игру: Моды -> Установить, найти
по имени, поставить (включать не обязательно). Архив ляжет в папку модов,
и следующий запуск этого скрипта подхватит из него locale/. Второй путь —
нажать Download на странице мода в браузере и положить zip в папку модов
вручную.
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


def main(argv):
    parser = argparse.ArgumentParser(add_help=True)
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

    if missing:
        print()
        print('Поставьте недостающие через игру: Моды -> Установить, найти по')
        print('имени, поставить (включать не обязательно). Потом запустите скрипт')
        print('снова. Качать с портала он не умеет: страницы загрузки закрыты')
        print('Cloudflare — 403 любому клиенту, кроме браузера и самой игры.')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
