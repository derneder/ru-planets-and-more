#!/usr/bin/env python3
"""Сборка zip-архива для загрузки на mods.factorio.com.

Использование:
    python3 tools/build.py

Портал требует, чтобы всё содержимое лежало ВНУТРИ одной папки с именем
«<name>_<version>». Просто заархивировать содержимое папки нельзя — портал
такой архив отклонит. Скрипт делает это правильно, беря имя и версию
из info.json.

Перед сборкой автоматически запускаются tools/check.py и tools/listing.py;
при найденных проблемах сборка прерывается. Заодно список dependencies
в info.json приводится к алфавитному порядку — см. sort_dependencies().
"""
import collections
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MOD = os.path.join(ROOT, 'mod')
DIST = os.path.join(ROOT, 'dist')

INFO = os.path.join(MOD, 'info.json')

# Префиксы зависимостей Factorio: «!» несовместимость, «?» необязательная,
# «(?)» скрытая необязательная, «~» не влияет на порядок загрузки.
# Обязательные идут первыми, несовместимости — последними, внутри группы
# сортировка по имени без учёта регистра: иначе Abacayba и canal-excavator
# разъезжаются по разным концам списка.
PREFIX_RANK = {'': 0, '~': 1, '?': 2, '(?)': 3, '!': 4}


def split_dependency(entry):
    """'? planet-muluna >= 1.0' -> ('?', 'planet-muluna >= 1.0')."""
    rest = entry.strip()
    for prefix in ('(?)', '!', '?', '~'):
        if rest.startswith(prefix):
            return prefix, rest[len(prefix):].strip()
    return '', rest


def sort_dependencies():
    """Раскладывает dependencies по алфавиту прямо в mod/info.json."""
    info = json.load(io.open(INFO, encoding='utf-8'),
                     object_pairs_hook=collections.OrderedDict)
    before = list(info.get('dependencies', []))
    if not before:
        return

    def key(entry):
        prefix, name = split_dependency(entry)
        return PREFIX_RANK.get(prefix, 9), name.lower()

    after = sorted(before, key=key)
    if after == before:
        print('Зависимости уже по алфавиту (%d).' % len(after))
        return

    info['dependencies'] = after
    io.open(INFO, 'w', encoding='utf-8', newline='\n').write(
        json.dumps(info, ensure_ascii=False, indent=2) + '\n')
    moved = sum(1 for a, b in zip(before, after) if a != b)
    print('Зависимости отсортированы: %d из %d строк сменили место.'
          % (moved, len(after)))


def main():
    sort_dependencies()
    print('Проверка перед сборкой...')
    sys.stdout.flush()
    result = subprocess.run([sys.executable, os.path.join(ROOT, 'tools', 'check.py')])
    if result.returncode != 0:
        print('\nСборка прервана: сначала исправьте проблемы выше.')
        return 1

    sys.stdout.flush()
    result = subprocess.run([sys.executable, os.path.join(ROOT, 'tools', 'listing.py'),
                             '--check'])
    if result.returncode != 0:
        print('\nСборка прервана: карточка портала разошлась с содержимым пакета.')
        return 1

    info = json.load(io.open(os.path.join(MOD, 'info.json'), encoding='utf-8'))
    folder = f'{info["name"]}_{info["version"]}'
    os.makedirs(DIST, exist_ok=True)
    archive = os.path.join(DIST, folder + '.zip')

    if os.path.exists(archive):
        os.remove(archive)

    with tempfile.TemporaryDirectory() as tmp:
        staged = os.path.join(tmp, folder)
        shutil.copytree(MOD, staged)
        with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as zf:
            for base, _dirs, names in os.walk(staged):
                for name in sorted(names):
                    if name == '.DS_Store':
                        continue
                    full = os.path.join(base, name)
                    zf.write(full, os.path.relpath(full, tmp))

    size = os.path.getsize(archive) / 1024
    print()
    print(f'Собрано: {archive}  ({size:.0f} КБ)')
    print(f'Папка внутри архива: {folder}/')

    print()
    sys.stdout.flush()
    result = subprocess.run([sys.executable, os.path.join(ROOT, 'tools', 'listing.py')])
    if result.returncode != 0:
        print('\nАрхив собран, но карточку портала собрать не удалось — '
              'см. сообщения выше.')
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
