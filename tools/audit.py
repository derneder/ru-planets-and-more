#!/usr/bin/env python3
"""Сплошная сверка русского перевода с английским оригиналом.

Проверяет ВСЕ общие ключи, а не только недостающие. Именно так были найдены
удвоенные проценты в Factorio Plus и выдуманное «в 2 раза» в Igrys.

Использование:
    python3 tools/audit.py EN.cfg RU.cfg [метка]

Что проверяется:
  ТЕГИ         набор тегов движка ([item=...], [color=...]) должен совпадать
  ПОДСТАНОВКИ  __1__, __CONTROL__... должны совпадать и по составу, и по числу
  ПЕРЕНОСЫ     количество \\n должно совпадать
  ЧИСЛА        цифры в тексте должны совпадать
  ПУСТО        непустое EN-значение не должно стать пустым
  НЕ ПЕРЕВЕДЕНО  русское значение дословно равно английскому
  ЛАТИНИЦА     остатки английских слов вне тегов
  НЕСОГЛАСОВАНО  одна английская строка переведена по-разному

Ложные срабатывания, которые встречаются регулярно (проверяйте глазами):
  - числа прописью: «sector 5» -> «в пятом секторе»
  - «Set to zero» -> «Установите 0»
  - разделитель тысяч: «10.000» -> «10 000»
  - научные и латинские имена: Cupriavidus necator
  - намеренно разные переводы для предмета и сущности (как в ванили:
    «Отвлекающая капсула» / «Отвлекатель»)
"""
import sys
import os
import re
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cfglib import (parse, total_keys, strip_markup, numbers,  # noqa: E402
                    ENGINE_TAG, PLACEHOLDER, iter_common)

# Слова, которые законно остаются латиницей: имена собственные, названия
# планет и модов, устоявшиеся термины. Список пополняйте по мере надобности —
# это просто фильтр шума, а не правило перевода.
ALLOWED_LATIN = {
    'Factorio', 'Factorioplus', 'Exotic', 'Industries', 'Space', 'Age',
    'Informatron', 'EI', 'Discord', 'Foundry', 'Planetaris', 'Krastorio',
    'Cupriavidus', 'necator', 'GitHub', 'MIT', 'Legacy',
    # планеты и луны
    'Nauvis', 'Gleba', 'Fulgora', 'Vulcanus', 'Aquilo',
    # устоявшиеся у игроков термины
    'deathworld', 'marathon', 'rail', 'world',
}


def audit(en_path, ru_path, label=None):
    en, ru = parse(en_path), parse(ru_path)
    label = label or os.path.basename(ru_path)
    issues = defaultdict(list)

    for section, key, v, r in iter_common(en, ru):
        if ENGINE_TAG.findall(v) != ENGINE_TAG.findall(r):
            issues['ТЕГИ'].append((section, key, v, r))
        if PLACEHOLDER.findall(v) != PLACEHOLDER.findall(r):
            issues['ПОДСТАНОВКИ'].append((section, key, v, r))
        if v.count('\\n') != r.count('\\n'):
            issues['ПЕРЕНОСЫ'].append((section, key, v, r))
        if v.strip() and not r.strip():
            issues['ПУСТО'].append((section, key, v, r))
        if numbers(v) != numbers(r):
            issues['ЧИСЛА'].append((section, key, v, r))
        if v.strip() == r.strip() and re.search(r'[A-Za-z]{4,}', strip_markup(v)):
            issues['НЕ ПЕРЕВЕДЕНО'].append((section, key, v, r))
        else:
            leftovers = [w for w in re.findall(r'[A-Za-z]{3,}', strip_markup(r))
                         if w not in ALLOWED_LATIN]
            if leftovers:
                issues['ЛАТИНИЦА'].append((section, key, v, r))

    # одна английская строка -> несколько разных русских
    mapping = defaultdict(set)
    for section, key, v, r in iter_common(en, ru):
        if v.strip():
            mapping[v.strip()].add(r.strip())
    inconsistent = [(v, rs) for v, rs in mapping.items() if len(rs) > 1]

    total = sum(len(x) for x in issues.values()) + len(inconsistent)
    print(f'===== {label}: замечаний {total} '
          f'(EN {total_keys(en)} / RU {total_keys(ru)}) =====')

    for category, items in issues.items():
        print(f'  -- {category}: {len(items)}')
        for section, key, v, r in items:
            print(f'     {section} {key}')
            print(f'        EN: {v[:150]}')
            print(f'        RU: {r[:150]}')

    if inconsistent:
        print(f'  -- НЕСОГЛАСОВАНО: {len(inconsistent)}')
        for v, rs in inconsistent:
            print(f'     EN: {v[:80]}')
            for variant in sorted(rs):
                print(f'        -> {variant[:80]}')
    print()
    return total


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 1
    label = sys.argv[3] if len(sys.argv) > 3 else None
    audit(sys.argv[1], sys.argv[2], label)
    return 0


if __name__ == '__main__':
    sys.exit(main())
