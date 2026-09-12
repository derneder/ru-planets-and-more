# Состояние проекта

Составлен по `reference/listing.json` и содержимому `mod/locale/ru/`.
Обновляйте при каждом релизе.

Актуально на версию **1.11.0**.

Всего: **31 мод**, **35 файлов** локализации, **4181 строка** перевода,
**30 необязательных** зависимостей.

## Переведены полностью — русского не было вообще

| Мод | Файлы | Строк |
|---|---|---|
| Exotic Space Industries | `exotic-space-industries.cfg`, `exotic-space-industries-emt.cfg`, `exotic-space-industries-fueler.cfg` | 1734 |
| Eneas | `moon-eneas.cfg`, `moon-eneas-dialogue.cfg`, `moon-eneas-informatron.cfg` | 585 |
| Dea Dia System | `dea-dia-system.cfg` | 284 |
| Abacayba, Moon of Nauvis | `abacayba.cfg` | 251 |
| Planet Erimos Prime | `planet-erimos-prime.cfg` | 86 |
| Planetaris: Красители | `planetaris-dyes.cfg` | 80 |
| Canal Excavator | `canal-excavator.cfg` | 41 |
| Carna APS | `carna-aps.cfg` | 24 |
| EON: Fulgora Discovered | `eon-fulgora-discovered.cfg` | 23 |
| Robocharger Updated | `robocharger-updated.cfg` | 18 |
| Far Reach | `far-reach.cfg` | 12 |
| Queue To Front (Limited) | `queue-to-front-limited.cfg` | 8 |
| Lamp Post | `lamp-post.cfg` | 5 |

## Дополнены и исправлены — перевод автора был неполным

| Мод | Файлы | Строк |
|---|---|---|
| Planetaris: Теллус | `planetaris-tellus.cfg` | 300 |
| Planetaris: Хайарион | `planetaris-hyarion.cfg` | 269 |
| Planetaris: Ариг | `planetaris-arig.cfg` | 195 |
| Lignumis | `lignumis.cfg` | 63 |
| Vesta | `skewer-planet-vesta.cfg` | 62 |
| SLP — Dyson Sphere Reworked | `slp-dyson-sphere-reworked.cfg` | 30 |
| Carna | `carna.cfg` | 25 |
| Igrys | `igrys.cfg` | 22 |
| Ледяные Кусаки | `cold-biters.cfg` | 22 |
| Factorio Plus | `factorioplus.cfg` | 22 |
| Арракис | `planet-arrakis.cfg` | 7 |

## Добавлено только название в списке модов

| Мод | Файлы | Строк |
|---|---|---|
| Церис, луна Фульгоры | `cerys-moon-of-fulgora.cfg` | 2 |
| Мулуна, луна Наувиса | `planet-muluna.cfg` | 2 |
| Мошайн | `moshine.cfg` | 2 |
| Кастра Прайм | `castra-prime.cfg` | 2 |
| Тенебрис Прайм | `tenebris-prime.cfg` | 2 |
| Терра Палус | `terrapalus.cfg` | 2 |
| Планета Линокс | `linox.cfg` | 1 |

## Что не сверено построчно

Для сверки нужен `locale/en/*.cfg` мода. Если мод не установлен и его
английского файла нет в `source-en/`, перевод остаётся непроверенным.
Проверить текущее состояние: `python3 tools/check.py`.
