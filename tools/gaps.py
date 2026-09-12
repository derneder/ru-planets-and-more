#!/usr/bin/env python3
"""Показывает ключи, которых нет в русском переводе.

Использование:
    python3 tools/gaps.py source-en/en_file.cfg source-en/ru_file.cfg
    python3 tools/gaps.py source-en/en_file.cfg          # русского нет вообще

Второй аргумент — СОБСТВЕННЫЙ русский файл мода (из его архива), а не наш
файл из mod/locale/ru. Смысл в том, чтобы найти, чего автору не хватило,
и дописать только это, не дублируя его работу.

Вывод готов к копированию: секции и строки ключ=английское значение.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cfglib import parse, total_keys  # noqa: E402


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1

    en = parse(sys.argv[1])
    ru = parse(sys.argv[2]) if len(sys.argv) > 2 else {}

    missing = [(s, k, v) for s in en for k, v in en[s].items()
               if k not in ru.get(s, {})]
    stale = [(s, k) for s in ru for k in ru[s] if k not in en.get(s, {})]

    print(f'EN: {total_keys(en)} ключей | RU: {total_keys(ru)} ключей')
    print(f'НЕ ПЕРЕВЕДЕНО: {len(missing)} | лишних в RU: {len(stale)}')
    print()

    if stale:
        # Обычно это либо устаревшие ключи, либо — что важнее — признак
        # опечатки в ключе английского файла (было такое с "Tarmac ").
        print('; Есть в русском, но нет в английском.')
        print('; Проверьте: возможно, в EN-ключе лишний пробел или опечатка.')
        for s, k in stale:
            print(f';   {s} {k}')
        print()

    current = None
    for section, key, value in missing:
        if section != current:
            print(section)
            current = section
        print(f'{key}={value}')

    return 0


if __name__ == '__main__':
    sys.exit(main())
