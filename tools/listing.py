#!/usr/bin/env python3
"""Сборка карточки мода для mods.factorio.com.

Использование:
    python3 tools/listing.py          # собрать карточку
    python3 tools/listing.py --check  # только проверить, ничего не писать

Данные берутся из четырёх мест и нигде не дублируются:

    mod/info.json                        версия, название
    mod/changelog.txt                    блок «Что нового» — верхняя запись
    reference/listing.json               список модов по группам, summary, faq
    reference/PORTAL-LISTING.template.md проза карточки с подстановками

Результат:

    dist/PORTAL-<version>.md             карточка под конкретный релиз (для глаз)
    reference/PORTAL-LISTING-FULL.md     та же карточка как актуальный справочник

    dist/portal-fields/summary.txt       ровно то, что уходит в поля
    dist/portal-fields/description.md    summary / description / faq
    dist/portal-fields/faq.md            эндпоинта edit_details

Файлы в portal-fields — без всякой обвязки, их содержимое отправляется как
есть; их читает tools/publish.py.

Заодно проверяется главное, что реально расходится от релиза к релизу:
каждый файл из mod/locale/ru/ должен быть упомянут в listing.json ровно один
раз. Добавили перевод и забыли про карточку — сборка упадёт и напомнит.

tools/build.py вызывает этот скрипт сам, отдельно запускать не обязательно.
"""
import datetime
import io
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MOD = os.path.join(ROOT, 'mod')
LOCALE = os.path.join(MOD, 'locale', 'ru')
REFERENCE = os.path.join(ROOT, 'reference')
DIST = os.path.join(ROOT, 'dist')

TEMPLATE = os.path.join(REFERENCE, 'PORTAL-LISTING.template.md')
DATA = os.path.join(REFERENCE, 'listing.json')
FULL = os.path.join(REFERENCE, 'PORTAL-LISTING-FULL.md')

GROUP_KEYS = ('full', 'partial', 'nameonly')
SUMMARY_LIMIT = 500


def read(path):
    return io.open(path, encoding='utf-8').read()


def write(path, text):
    io.open(path, 'w', encoding='utf-8', newline='\n').write(text)


def mods_word(n):
    """«31 мода», но «29 модов» — родительный после числительного."""
    return 'мода' if n % 10 == 1 and n % 100 != 11 else 'модов'


def cfg_files():
    return sorted(f for f in os.listdir(LOCALE) if f.endswith('.cfg'))


def latest_changelog(text):
    """Верхняя запись changelog.txt -> (версия, тело без строк Version/Date)."""
    blocks = [b.strip('\n') for b in re.split(r'^-{20,}$', text, flags=re.M)
              if b.strip()]
    if not blocks:
        return None, ''
    head = blocks[0]
    version = re.search(r'^Version:\s*(\S+)', head, re.M)
    body = [l for l in head.split('\n')
            if not re.match(r'^(Version|Date):', l.strip())]
    while body and not body[0].strip():
        body.pop(0)
    return (version.group(1) if version else None), '\n'.join(body).rstrip()


def render_group(entries):
    out = []
    for e in entries:
        line = '- **%s**' % e['name']
        if e.get('note'):
            line += ' — %s' % e['note']
        out.append(line)
    return '\n'.join(out)


def extract_description(card):
    """Тело поля Description — первый ``` блок после заголовка Description."""
    head = card.find('## Description')
    if head < 0:
        return None
    block = re.search(r'^```\s*\n(.*?)^```\s*$', card[head:], re.S | re.M)
    return block.group(1).rstrip() if block else None


def validate(data, info):
    """Возвращает список проблем. Пусто — значит всё сходится."""
    problems = []

    listed = []
    for key in GROUP_KEYS:
        if key not in data['groups']:
            problems.append('в listing.json нет группы "%s"' % key)
            continue
        for entry in data['groups'][key]:
            if not entry.get('files'):
                problems.append('у записи "%s" не указан ни один файл'
                                % entry.get('name', '?'))
            listed.extend(entry.get('files', []))

    on_disk = cfg_files()

    for f in sorted(set(on_disk) - set(listed)):
        problems.append('файл %s не упомянут в reference/listing.json '
                        '— в какую группу карточки он идёт?' % f)
    for f in sorted(set(listed) - set(on_disk)):
        problems.append('в listing.json указан несуществующий файл %s' % f)
    for f in sorted({f for f in listed if listed.count(f) > 1}):
        problems.append('файл %s упомянут в listing.json больше одного раза' % f)

    # Веха нужна на каждую минорную версию. Патчи (1.10.1 при вехе 1.10.0)
    # наследуют веху своей минорной — иначе список вех зарастает мелочью.
    version = info['version']
    minor = '.'.join(version.split('.')[:2]) + '.'
    if not any(rel.startswith('**%s**' % version)
               or rel.startswith('**%s' % minor) for rel in data['releases']):
        problems.append('в "releases" нет вехи ни про %s, ни про ветку %sx '
                        '— добавьте строку' % (version, minor))

    for field in ('summary', 'faq', 'source_url'):
        if not data.get(field, '').strip():
            problems.append('в listing.json пустое поле "%s"' % field)

    count = sum(len(data['groups'][k]) for k in GROUP_KEYS if k in data['groups'])
    summary = (data.get('summary', '').replace('{{MOD_COUNT}}', str(count))
               .replace('{{MOD_WORD}}', mods_word(count)))
    if len(summary) > SUMMARY_LIMIT:
        problems.append('summary длиннее %d символов (сейчас %d) — портал обрежет'
                        % (SUMMARY_LIMIT, len(summary)))

    return problems


def main(argv):
    check_only = '--check' in argv

    info = json.loads(read(os.path.join(MOD, 'info.json')))
    data = json.loads(read(DATA))

    problems = validate(data, info)
    if problems:
        print('Карточка портала: расхождения\n')
        for p in problems:
            print('  - ' + p)
        return 1

    chg_version, chg_body = latest_changelog(
        read(os.path.join(MOD, 'changelog.txt')))
    if chg_version != info['version']:
        print('Карточка портала: в changelog.txt верхняя запись — версия %s, '
              'а в info.json — %s.' % (chg_version, info['version']))
        return 1

    count = sum(len(data['groups'][k]) for k in GROUP_KEYS)
    if check_only:
        print('Карточка портала: данные сходятся (%d %s, %d файлов).'
              % (count, mods_word(count), len(cfg_files())))
        return 0

    archive = 'ru-planets-and-more_%s.zip' % info['version']
    subs = {
        'VERSION': info['version'],
        'ARCHIVE': archive,
        'TITLE': info['title'],
        'MOD_COUNT': str(count),
        'MOD_WORD': mods_word(count),
        'FILE_COUNT': str(len(cfg_files())),
        'GROUP_FULL': render_group(data['groups']['full']),
        'GROUP_PARTIAL': render_group(data['groups']['partial']),
        'GROUP_NAMEONLY': render_group(data['groups']['nameonly']),
        'RELEASES': '\n'.join('- ' + r for r in data['releases']),
        'LATEST_CHANGES': chg_body,
        'GENERATED': datetime.date.today().isoformat(),
        'FAQ': data['faq'].rstrip(),
    }
    subs['SUMMARY'] = (data['summary']
                       .replace('{{MOD_COUNT}}', subs['MOD_COUNT'])
                       .replace('{{MOD_WORD}}', subs['MOD_WORD']))

    text = read(TEMPLATE)
    text = re.sub(r'^<!--.*?-->\n', '', text, count=1, flags=re.S)
    for key, value in subs.items():
        text = text.replace('{{%s}}' % key, value)

    left = re.findall(r'\{\{(\w+)\}\}', text)
    if left:
        print('Карточка портала: в шаблоне остались незаполненные подстановки: '
              + ', '.join(sorted(set(left))))
        return 1

    description = extract_description(text)
    if description is None:
        print('Карточка портала: в шаблоне не нашёлся ``` блок под заголовком '
              '"## Description" — поле для API собрать не из чего.')
        return 1

    os.makedirs(DIST, exist_ok=True)
    release_card = os.path.join(DIST, 'PORTAL-%s.md' % info['version'])
    write(release_card, text)
    write(FULL, text)

    fields = os.path.join(DIST, 'portal-fields')
    os.makedirs(fields, exist_ok=True)
    for name, value in (('summary', subs['SUMMARY']), ('faq', data['faq']),
                        ('description', description)):
        left_over = re.findall(r'\{\{(\w+)\}\}', value)
        if left_over:
            print('Карточка портала: в поле %s остались подстановки: %s'
                  % (name, ', '.join(sorted(set(left_over)))))
            return 1
    write(os.path.join(fields, 'summary.txt'), subs['SUMMARY'] + '\n')
    write(os.path.join(fields, 'description.md'), description + '\n')
    write(os.path.join(fields, 'faq.md'), data['faq'].rstrip() + '\n')
    write(os.path.join(fields, 'source_url.txt'), data['source_url'].strip() + '\n')

    print('Карточка портала: %s' % release_card)
    print('Справочник обновлён: %s' % os.path.relpath(FULL, ROOT))
    print('Поля для edit_details: %s (summary %d симв., description %d, faq %d)'
          % (os.path.relpath(fields, ROOT), len(subs['SUMMARY']),
             len(description), len(data['faq'])))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
