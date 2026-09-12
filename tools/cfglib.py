"""Общие функции для работы с файлами локализации Factorio (.cfg).

Формат: ini-подобный, секции в квадратных скобках, строки вида ключ=значение.
Кодировка UTF-8. Переносы строк внутри значений записываются как \\n
(ОДИН обратный слеш — см. docs/PITFALLS.md).
"""
import io
import re
from collections import defaultdict

# Настоящие теги движка. Всё остальное в квадратных скобках — просто текст
# (например "[Прочтите меня]"), его переводить можно и нужно.
ENGINE_TAG = re.compile(
    r'\[(?:'
    r'/?color(?:=[^\]]*)?'
    r'|/?font(?:=[^\]]*)?'
    r'|img=[^\]]*'
    r'|item=[^\]]*'
    r'|entity=[^\]]*'
    r'|fluid=[^\]]*'
    r'|planet=[^\]]*'
    r'|tile=[^\]]*'
    r'|technology=[^\]]*'
    r'|recipe=[^\]]*'
    r'|virtual-signal=[^\]]*'
    r'|achievement=[^\]]*'
    r'|gps=[^\]]*'
    r'|space-location=[^\]]*'
    r'|quality=[^\]]*'
    r')\]'
)

PLACEHOLDER = re.compile(r'__[A-Za-z0-9_]+?__')
NUMBER = re.compile(r'\d+[.,]?\d*')


def parse(path):
    """Читает cfg в словарь {секция: {ключ: значение}}.

    Порядок ключей сохраняется (обычные dict в Python 3.7+ упорядочены).
    Комментарии (;) и пустые строки пропускаются.
    """
    sections = {}
    current = None
    for raw in io.open(path, encoding='utf-8', errors='replace'):
        line = raw.rstrip('\r\n').strip()
        if not line or line.startswith(';'):
            continue
        if line.startswith('['):
            current = line
            sections.setdefault(current, {})
            continue
        if '=' in line and current is not None:
            key, value = line.split('=', 1)
            sections[current][key] = value
    return sections


def total_keys(sections):
    return sum(len(v) for v in sections.values())


def strip_markup(value):
    """Убирает теги и подстановки — остаётся только человеческий текст."""
    text = re.sub(r'\[[^\]]*\]', '', value)
    text = PLACEHOLDER.sub('', text)
    return text.replace('\\n', ' ')


def numbers(value):
    """Числа без хвостовой пунктуации, запятая приведена к точке."""
    return [n.rstrip('.,').replace(',', '.') for n in NUMBER.findall(value)]


def find_duplicate_keys(path):
    """Дубли ключей внутри одного файла (секция + ключ встречаются дважды)."""
    seen = defaultdict(int)
    current = None
    for raw in io.open(path, encoding='utf-8', errors='replace'):
        line = raw.rstrip('\r\n').strip()
        if not line or line.startswith(';'):
            continue
        if line.startswith('['):
            current = line
            continue
        if '=' in line and current is not None:
            seen[(current, line.split('=', 1)[0])] += 1
    return {k: n for k, n in seen.items() if n > 1}


def iter_common(en, ru):
    """Проходит по ключам, которые есть и в английском, и в русском."""
    for section, pairs in en.items():
        for key, en_value in pairs.items():
            if key in ru.get(section, {}):
                yield section, key, en_value, ru[section][key]
