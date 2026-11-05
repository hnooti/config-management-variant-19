# Граф зависимостей NuGet

**Конфигурационное управление · практическая работа № 2 · вариант 19**

РТУ МИРЭА · 2 курс · ИКБО-62-25

Репозиторий: [github.com/hnooti/config-management-variant-19][repo].

Утилита строит граф прямых и транзитивных зависимостей выбранной версии
.NET-пакета. В сетевом режиме она сама запрашивает NuGet V3 и читает XML
`.nuspec` стандартной библиотекой Python. В локальном режиме она читает
заданный JSON. Обход в ширину идёт рекурсивно по уровням. Результат можно
сохранить в DOT и SVG, вывести деревом или упорядочить для загрузки.

## Запуск и настройки

Требуется **Python 3.10+**. Сборка и установка Python-библиотек не нужны.
Для создания SVG нужен [Graphviz][graphviz] с командой `dot` в `PATH`.
На macOS его можно установить командой `brew install graphviz`.
Для режимов просмотра и тестов Graphviz не требуется.

```sh
./run.sh examples/configuration.ini
python3 -m unittest discover -s tests -v
```

Запасная команда запуска из корня проекта: `python3 -m src examples/configuration.ini`.
Настройки берутся из секции `[graph]` файла INI в UTF-8.

| Ключ | Назначение | Пример неверного значения |
| --- | --- | --- |
| `package` | ID NuGet; в тестовом режиме имя из A–Z | `bad name` |
| `repository` | URL индекса NuGet V3 или путь к файлу JSON | `file:///a` в сетевом режиме |
| `test_mode` | `true` — JSON, `false` — NuGet | `maybe` |
| `version` | Точная версия, например `8.0.0`; в JSON условная | `latest` |
| `output` | Путь к файлу `.svg`; рядом сохраняется `.dot` | `graph.png` |
| `ascii_tree` | Печатать ASCII-дерево: `true` или `false` | `maybe` |
| `max_depth` | От 0 до 500; глубина корня — 0 | `-1` |
| `target_framework` | Необязательное точное имя группы, например `net8.0` | `not a TFM` |

Относительные пути внутри INI считаются от каталога этого INI. Пустой
`target_framework` объединяет зависимости всех групп. При заданном имени
используется точная группа либо общие зависимости, если они есть.

| Режим | Результат |
| --- | --- |
| Без флага | Файлы SVG и DOT; при `ascii_tree = true` также дерево в консоли |
| `--show-config` | Проверка INI и вывод `ключ=значение` без сетевых запросов |
| `--direct` | Прямые зависимости и исходные ограничения версий |
| `--levels` | Вершины в порядке BFS с указанием глубины |
| `--load-order` | Топологический порядок: зависимости раньше потребителей |

## Локальные сценарии

Тестовый репозиторий — JSON-объект, в котором ключи задают пакеты, значения
задают списки прямых зависимостей. Для каждой вершины, включая лист,
нужна отдельная запись. Пример: `{"A":["B"],"B":[]}`.

```sh
./run.sh examples/diamond.ini --show-config
./run.sh examples/configuration.ini --direct
./run.sh examples/diamond.ini --levels
./run.sh examples/diamond.ini --load-order
./run.sh examples/depth-one.ini --load-order
./run.sh examples/cycle.ini --load-order
```

| Сценарий | Что видно при запуске |
| --- | --- |
| `diamond.ini` | BFS: A → B, C → уровень D, E. Обе связи к D сохранены. Порядок: D, E, B, C, A. |
| `depth-one.ini` | Видны A, B, C. Порядок B, C, A сопровождается предупреждением об отсечении. |
| `cycle.ini` | Сохранена связь C → A. Для порядка выводится ошибка и код завершения 1. |

`--show-config` проверяет все поля. Например, если в копии INI указать
`max_depth = -1`, команда завершится с сообщением
`Ошибка: max_depth: допустимы значения от 0 до 500`.
Ошибочные значения из таблицы проверяет `tests/test_config.py`.

Уровень BFS раскрывается целиком перед рекурсивным переходом к следующему.
Посещённую вершину (ID + версия) повторно не запрашиваем, но сохраняем
каждое входящее ребро. Вершины на пределе глубины видны, их потомки
не запрашиваются. Для порядка загрузки алгоритм Кана начинает с вершин
без зависимостей и завершает работу ошибкой, если остаётся цикл.

| Модуль | За что отвечает |
| --- | --- |
| `config`, `__main__` | Проверка INI, обработка аргументов, вывод результата или ошибки |
| `nuget`, `nuspec`, `version` | HTTP, разбор XML и выбор минимальной подходящей версии на ребре |
| `test_repository` | Проверка списка смежности и чтение тестовых соседей |
| `graph`, `order` | Рекурсивный BFS и топологическая сортировка |
| `visualize` | DOT, вызов Graphviz для SVG, ASCII-дерево |

## Визуализация трёх пакетов

Все примеры используют NuGet.org, версию **8.0.0** и группу **net8.0**.
Команда печатает пути к файлам, а SVG можно открыть в браузере.
Стрелка ведёт от пакета к его зависимости. Синим выделен корень;
пунктир отмечает вершины, не раскрытые из-за ограничения глубины.

```sh
./run.sh examples/configuration.ini
./run.sh examples/injection.ini
./run.sh examples/logging.ini
```

| Входной файл | Пакет (префикс Microsoft.Extensions.) | Файлы в `out/` |
| --- | --- | --- |
| `configuration.ini` | Configuration | `configuration.dot`, `configuration.svg` |
| `injection.ini` | DependencyInjection | `injection.dot`, `injection.svg` |
| `logging.ini` | Logging | `logging.dot`, `logging.svg` |

Деревья ниже сокращены для чтения: опущены префикс `Microsoft.Extensions.`
и версия `8.0.0`. Метка `[seen]` означает, что пакет уже показан выше;
`[cycle]` отмечает возврат к предку, `[depth limit]` — границу BFS.

```text
Configuration
|-- Configuration.Abstractions
|   `-- Primitives
`-- Primitives [seen]

DependencyInjection
`-- DependencyInjection.Abstractions

Logging
|-- DependencyInjection
|   `-- DependencyInjection.Abstractions
|-- Logging.Abstractions
|   `-- DependencyInjection.Abstractions [seen]
`-- Options
    |-- DependencyInjection.Abstractions [seen]
    `-- Primitives
```

## Сверка с NuGet

Сверка выполнена на **.NET SDK 8.0.427** для отдельных проектов `net8.0`
с точной ссылкой `[8.0.0]`. Следующие команды требуют .NET SDK 8.0.4xx
или новее с поддержкой `net8.0`; самой программе .NET SDK не нужен.

```sh
./examples/compare-dotnet.sh configuration
./examples/compare-dotnet.sh injection
./examples/compare-dotnet.sh logging
./run.sh examples/logging.ini --load-order
```

Скрипт создаёт временный проект, запускает `dotnet restore` с пустым
каталогом пакетов, показывает `dotnet list package --include-transitive`
и [`dotnet nuget why`][why], затем печатает рёбра из `project.assets.json`.
Наборы пакетов, версии и рёбра совпали для всех трёх примеров.

| Пакет | Вершины, включая корень | Рёбра | Проверенный путь в `dotnet nuget why` |
| --- | ---: | ---: | --- |
| Configuration | 3 | 3 | До Primitives есть прямой путь и путь через Configuration.Abstractions |
| DependencyInjection | 2 | 1 | До DependencyInjection.Abstractions идёт одно ребро |
| Logging | 6 | 7 | До DependencyInjection.Abstractions есть три пути |

Штатная команда показывает пути от проекта до **выбранного** пакета.
Наш SVG показывает весь граф от корневого пакета: общий потомок изображён
одной вершиной, к которой ведут все рёбра. Различается вид представления,
а связи для проверенных примеров одинаковы.

В одном запуске `dotnet restore` строки `Installed` для Configuration
и DependencyInjection шли в том же порядке, что и `--load-order`.
Для Logging программа ставит Options и Logging.Abstractions раньше Logging.
В журнале NuGet Logging появился раньше обоих. `Installed` фиксирует
завершение установки в локальный каталог, поэтому порядок строк может
зависеть от параллельной работы и времени загрузки. Наша команда
показывает порядок, в котором каждое ребро соблюдено.

### Границы реализации

При анализе каждого ребра выбирается минимальная подходящая версия.
Поддерживаются точные версии, минимумы и интервалы; плавающие версии
не поддерживаются. Программа не объединяет ограничения разных ветвей
в одну версию и не подбирает ближайшую совместимую группу платформы.
При конфликтах версий или несовпадении платформ результат может
отличаться от [правил восстановления NuGet][resolution].

Реализация протокола основана на описании [PackageBaseAddress][v3].
В истории Git выделены пять этапов: INI, метаданные NuGet, BFS,
порядок загрузки и визуализация.

[repo]: https://github.com/hnooti/config-management-variant-19
[graphviz]: https://graphviz.org/download/
[why]: https://learn.microsoft.com/dotnet/core/tools/dotnet-nuget-why
[resolution]: https://learn.microsoft.com/nuget/concepts/dependency-resolution
[v3]: https://learn.microsoft.com/nuget/api/package-base-address-resource
