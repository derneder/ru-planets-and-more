#!/usr/bin/env python3
"""Отправка на mods.factorio.com по API.

    python3 tools/publish.py                  # показать, что уйдёт (ничего не шлёт)
    python3 tools/publish.py --details --yes  # обновить summary/description/faq
    python3 tools/publish.py --release --yes  # залить архив текущей версии
    python3 tools/publish.py --all --yes      # и то, и другое

Без --yes скрипт работает вхолостую: печатает, что и куда ушло бы, и выходит.
Это сделано намеренно: релиз сразу виден подписчикам, а второй раз тот же номер
версии портал не примет, пока предыдущий не удалён.

Откатить можно, но только руками. Удалить релиз получится на странице мода:
портал не даёт удалить мод целиком, а вот отдельные версии — даёт, после чего
номер освобождается. В API удаления нет вовсе, документированы ровно два
эндпоинта — init_upload и finish_upload. Описание (edit_details), наоборот,
можно перезаписывать сколько угодно, это обычная правка текста.

КЛЮЧ НИКОГДА НЕ ХРАНИТСЯ В ПРОЕКТЕ. Берётся из переменной окружения
FACTORIO_API_KEY, а если её нет — из файла ~/.factorio-api-key (одна строка).
Ключ создаётся на https://factorio.com/profile, нужны права:

    ModPortal: Edit Mods     для --details
    ModPortal: Upload Mods   для --release

Что отправляется (собирается в tools/listing.py и tools/build.py):

    dist/portal-fields/summary.txt      -> поле summary
    dist/portal-fields/description.md   -> поле description
    dist/portal-fields/faq.md           -> поле faq
    dist/ru-planets-and-more_<v>.zip    -> новый релиз

Changelog отдельным полем не передаётся: портал строит вкладку Changelog сам
из changelog.txt внутри архива.
"""
import argparse
import io
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MOD = os.path.join(ROOT, 'mod')
DIST = os.path.join(ROOT, 'dist')
FIELDS = os.path.join(DIST, 'portal-fields')

EDIT_DETAILS = 'https://mods.factorio.com/api/v2/mods/edit_details'
INIT_UPLOAD = 'https://mods.factorio.com/api/v2/mods/releases/init_upload'

KEY_FILE = os.path.join(os.path.expanduser('~'), '.factorio-api-key')


def read(path):
    return io.open(path, encoding='utf-8').read()


def api_key():
    key = os.environ.get('FACTORIO_API_KEY', '').strip()
    if key:
        return key, 'переменная окружения FACTORIO_API_KEY'
    if os.path.exists(KEY_FILE):
        key = read(KEY_FILE).strip()
        if key:
            return key, KEY_FILE
    return None, None


def require(path, what):
    if not os.path.exists(path):
        print('Нет файла %s — %s. Сначала: python3 tools/build.py'
              % (os.path.relpath(path, ROOT), what))
        sys.exit(1)
    return path


def post(url, key, fields, files=None):
    """POST multipart/form-data только на стандартной библиотеке."""
    import uuid
    import urllib.request

    boundary = uuid.uuid4().hex
    body = bytearray()
    for name, value in fields.items():
        body += ('--%s\r\nContent-Disposition: form-data; name="%s"\r\n\r\n'
                 % (boundary, name)).encode('utf-8')
        body += value.encode('utf-8') + b'\r\n'
    for name, (filename, payload) in (files or {}).items():
        body += ('--%s\r\nContent-Disposition: form-data; name="%s"; '
                 'filename="%s"\r\nContent-Type: application/octet-stream\r\n\r\n'
                 % (boundary, name, filename)).encode('utf-8')
        body += payload + b'\r\n'
    body += ('--%s--\r\n' % boundary).encode('utf-8')

    request = urllib.request.Request(url, data=bytes(body), method='POST')
    request.add_header('Content-Type',
                       'multipart/form-data; boundary=%s' % boundary)
    if key:
        request.add_header('Authorization', 'Bearer %s' % key)
    try:
        with urllib.request.urlopen(request) as response:
            return json.loads(response.read().decode('utf-8'))
    except Exception as exc:  # noqa: BLE001 — портал отвечает телом и на 4xx
        detail = getattr(exc, 'read', None)
        if detail:
            try:
                return json.loads(detail().decode('utf-8'))
            except Exception:
                pass
        return {'error': type(exc).__name__, 'message': str(exc)}


def show(title, text, limit=180):
    body = text.strip().replace('\n', ' ')
    tail = '…' if len(body) > limit else ''
    print('  %-12s %5d симв.  %s%s' % (title, len(text), body[:limit], tail))


def main(argv):
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument('--details', action='store_true',
                        help='обновить summary, description и faq')
    parser.add_argument('--release', action='store_true',
                        help='залить архив текущей версии как новый релиз')
    parser.add_argument('--all', action='store_true', help='и то, и другое')
    parser.add_argument('--yes', action='store_true',
                        help='действительно отправить; без него — вхолостую')
    args = parser.parse_args(argv)

    details = args.details or args.all
    release = args.release or args.all
    if not details and not release:
        details = release = True

    info = json.loads(read(os.path.join(MOD, 'info.json')))
    name, version = info['name'], info['version']

    print('Мод: %s, версия %s' % (name, version))
    print()

    payload = {}
    if details:
        payload = {
            'summary': read(require(os.path.join(FIELDS, 'summary.txt'),
                                    'не собрана врезка')),
            'description': read(require(os.path.join(FIELDS, 'description.md'),
                                        'не собрано описание')),
            'faq': read(require(os.path.join(FIELDS, 'faq.md'), 'не собран FAQ')),
        }
        print('edit_details -> %s' % EDIT_DETAILS)
        for field, text in payload.items():
            show(field, text)
        print()

    archive = os.path.join(DIST, '%s_%s.zip' % (name, version))
    if release:
        require(archive, 'архив не собран')
        print('init_upload  -> %s' % INIT_UPLOAD)
        print('  архив       %s (%.0f КБ)'
              % (os.path.basename(archive), os.path.getsize(archive) / 1024))
        print()

    if not args.yes:
        print('Вхолостую: ничего не отправлено. Повторите с --yes.')
        return 0

    key, source = api_key()
    if not key:
        print('Ключ не найден. Задайте переменную окружения FACTORIO_API_KEY '
              'или положите ключ одной строкой в %s' % KEY_FILE)
        return 1
    print('Ключ взят: %s' % source)
    print()

    if details:
        result = post(EDIT_DETAILS, key, dict(payload, mod=name))
        if not result.get('success'):
            print('edit_details не прошёл: %s — %s'
                  % (result.get('error'), result.get('message')))
            return 1
        print('Описание обновлено: %s' % result.get('url', ''))

    if release:
        init = post(INIT_UPLOAD, key, {'mod': name})
        url = init.get('upload_url')
        if not url:
            print('init_upload не прошёл: %s — %s'
                  % (init.get('error'), init.get('message')))
            return 1
        with open(archive, 'rb') as handle:
            blob = handle.read()
        result = post(url, None, {}, {'file': (os.path.basename(archive), blob)})
        if not result.get('success'):
            print('Загрузка релиза не прошла: %s — %s'
                  % (result.get('error'), result.get('message')))
            return 1
        print('Релиз %s загружен.' % version)

    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
