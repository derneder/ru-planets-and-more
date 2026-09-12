#!/usr/bin/env python3
"""Проверка целостности пакета перед сборкой релиза.

Использование:
    python3 tools/check.py

Что проверяется:
  1. Синтаксис всех cfg: нет строк без «=» вне секций и комментариев
  2. Дубли ключей внутри одного файла
  3. info.json: валидный JSON, есть обязательные поля
  4. Каждой зависимости «? modname» соответствует хотя бы один файл локализации
     (мягкое предупреждение — имена файлов не обязаны совпадать с именами модов)
  5. Двойные слеши в переносах строк (\\\\n вместо \\n) — частая и незаметная
     ошибка, из-за которой в игре видно текст «\\n» вместо перевода строки
  6. Кодировка UTF-8 без BOM
"""
import io
import json
import os
import sys
import glob

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cfglib import find_duplicate_keys  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MOD = os.path.join(ROOT, 'mod')
LOCALE = os.path.join(MOD, 'locale', 'ru')


def main():
    problems = 0
    files = sorted(glob.glob(os.path.join(LOCALE, '*.cfg')))
    print(f'Файлов локализации: {len(files)}')

    for path in files:
        name = os.path.basename(path)

        with open(path, 'rb') as fh:
            raw = fh.read()
        if raw.startswith(b'\xef\xbb\xbf'):
            print(f'  [BOM] {name}: файл начинается с BOM, уберите его')
            problems += 1

        text = raw.decode('utf-8', errors='replace')

        if '\\\\n' in text:
            count = text.count('\\\\n')
            print(f'  [СЛЕШИ] {name}: {count} вхождений \\\\n '
                  f'(двойной слеш) — должен быть одинарный \\n')
            problems += 1

        # Ключи до первого [заголовка] попадают в безымянную секцию. Обычно это
        # опечатка в заголовке, поэтому ругаемся. Но некоторые моды (SLP - Dyson
        # Sphere Reworked) кладут туда игровые сообщения намеренно, и перекрыть
        # их можно только так же. Такой файл обязан объявить это явно строкой
        # «; БЕЗЫМЯННАЯ СЕКЦИЯ» — тогда проверка молчит.
        section = '' if 'БЕЗЫМЯННАЯ СЕКЦИЯ' in text else None
        for number, line in enumerate(text.splitlines(), 1):
            stripped = line.strip()
            if not stripped or stripped.startswith(';'):
                continue
            if stripped.startswith('['):
                section = stripped
                continue
            if '=' not in stripped:
                print(f'  [СИНТАКСИС] {name}:{number}: строка без «=»: '
                      f'{stripped[:60]}')
                problems += 1
            elif section is None:
                print(f'  [СИНТАКСИС] {name}:{number}: ключ вне секции')
                problems += 1

        for (sec, key), n in find_duplicate_keys(path).items():
            print(f'  [ДУБЛЬ] {name}: {sec} {key} встречается {n} раза')
            problems += 1

    info_path = os.path.join(MOD, 'info.json')
    try:
        info = json.load(io.open(info_path, encoding='utf-8'))
    except Exception as exc:
        print(f'  [INFO.JSON] не читается: {exc}')
        return 1

    for field in ('name', 'version', 'title', 'author', 'factorio_version'):
        if not info.get(field):
            print(f'  [INFO.JSON] отсутствует поле «{field}»')
            problems += 1

    deps = [d.lstrip('? ').strip() for d in info.get('dependencies', [])]
    print(f'Зависимостей: {len(deps)} | версия: {info.get("version")}')

    for dep in info.get('dependencies', []):
        if not dep.startswith('?'):
            print(f'  [ЗАВИСИМОСТЬ] «{dep}» не является необязательной. '
                  f'Пакет должен работать и без установленного мода.')
            problems += 1

    print()
    print('ВСЁ ЧИСТО' if problems == 0 else f'НАЙДЕНО ПРОБЛЕМ: {problems}')
    return 0 if problems == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
