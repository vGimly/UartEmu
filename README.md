UART Emulator

Эмулятор UART-устройства с TCP-интерфейсом, бинарным кадровым протоколом, динамически перезагружаемым application-слоем и HTTP API для управления и диагностики.

Проект предназначен для разработки и тестирования клиентских UART-утилит без наличия реального устройства BMC.

## Архитектура

```text
                    HTTP API
                       │
                       ▼
                 ┌───────────┐
                 │  api.py   │
                 └─────┬─────┘
                       │
                       ▼
                 ┌───────────┐
                 │app_loader │
                 └─────┬─────┘
                       │
                       ▼
                 ┌──────────────┐
                 │ application  │
                 └──────┬───────┘
                        │
                        ▼
                    ┌───────┐
                    │ state │
                    └───────┘

TCP :7000
    │
    ▼
┌───────────┐
│  uart.py  │
└─────┬─────┘
      │
      ▼
┌──────────────┐
│  protocol.py │
└──────┬───────┘
       │
       ▼
  application
```

### Основные компоненты

* `uart.py` — TCP-сервер, имитирующий UART.
* `protocol.py` — разбор и формирование UART-кадров.
* `application.py` — логика команд виртуального устройства.
* `app_loader.py` — загрузка и перезагрузка application-слоя без остановки UART-сервера.
* `api.py` — HTTP API управления эмулятором.
* `state.py` — постоянное хранилище состояния устройства.
* `main.py` — запуск HTTP API и UART-сервера.
* `t/` — тесты.

## Запуск

Проект использует Python virtual environment.

Создание окружения и установка зависимостей:

```bash
make init
```

Запуск сервера:

```bash
make run
```

Запуск в `screen`:

```bash
make start
```

Сервер запускается примерно так:

```text
HTTP API: 127.0.0.1:8000
UART:     10.9.0.1:7000
```

HTTP API намеренно слушает только loopback.

UART доступен клиентам по адресу `10.9.0.1:7000`.

Для разработки можно использовать Uvicorn reload:

```bash
.venv/bin/uvicorn main:app \
    --host 127.0.0.1 \
    --port 8000 \
    --reload
```

При изменении Python-кода перезагружается application/server layer, но существующий TCP UART-сервис не должен требовать переподключения клиента.

## UART-клиент

Для подключения к TCP UART удобно использовать `socat`:

```bash
make client
```

Это создаёт локальный pseudo-terminal:

```text
./uart0
```

который подключён к:

```text
10.9.0.1:7000
```

После этого клиентскую UART-утилиту можно направить на:

```text
./uart0
```

## Протокол

Кадр имеет вид:

```text
START CMD PAYLOAD CRC16 STOP
```

где:

```text
START = 0x7e
STOP  = 0x7e
ESC   = 0x7d
```

Данные между `START` и `STOP` передаются с escaping.

### Escaping

Зарезервированные байты кодируются escape-последовательностью:

```text
0x7e → 0x7d 0x5e
0x7d → 0x7d 0x5d
```

Неизвестная escape-последовательность считается ошибкой протокола.

### CRC16

CRC вычисляется по данным кадра согласно реализации `protocol.py`.

CRC передаётся двумя байтами.

При проверке используется исходное значение CRC до escaping.

### Ошибки протокола

Эмулятор генерирует error event при ошибках входного потока.

Коды:

```text
0x80  timeout
0x81  short frame
0x82  bad CRC
0x83  invalid escape
```

Также отдельно диагностируется мусор, поступающий до `START`.

Ответ об ошибке формируется как обычный UART-кадр:

```text
START
FF
error_code
CRC16
STOP
```

То есть:

```text
0x7e 0xff <error_code> <crc16> 0x7e
```

Все ошибки и переходы parser state подробно логируются.

## Команды

### Команда `0x01`

Простейшая echo-команда.

```text
request:
01 <payload>

response:
01 OK=<payload>
```

Например:

```text
01 hello
```

возвращает:

```text
01 OK=hello
```

### Команда `0x02`

Работа с регистром состояния.

`0x02` — идентификатор регистра.

Первый байт payload определяет операцию:

```text
0x01 = read
0x02 = write
```

После operation могут присутствовать до пяти байтов `0x00`, которые игнорируются.

#### Read

```text
02 01
```

Ответ содержит текущее значение регистра в ASCII:

```text
02 "-123"
```

#### Write

```text
02 02 "-123"
```

После успешной записи возвращается ACK:

```text
02
```

Значение передаётся как signed decimal ASCII.

Например:

```text
-512
-123
0
42
511
```

При некорректном значении команда остаётся валидной командой, но возвращает:

```text
-1
```

`None` для такой ошибки не используется, поскольку клиент должен получить ответ.

### Команда `0x03`

Возвращает локальные дату и время эмулятора:

```text
YYYYMMDD HHMMSS
```

Например:

```text
20260904 181505
```

## Состояние устройства

Состояние хранится в `state.py`.

Для хранения используется SQLite.

Это позволяет:

* сохранять состояние после перезапуска;
* атомарно выполнять read/write;
* хранить несколько регистров;
* не связывать состояние с TCP-соединением.

Текущий state является общим для эмулятора.

То есть два UART-клиента видят одно и то же состояние устройства.

## Application layer

`uart.py` не содержит реализации команд.

После успешного разбора кадра он передаёт команду в application layer:

```python
application.command(client, cmd, payload)
```

Это позволяет изменять поведение виртуального устройства без изменения UART transport/protocol слоя.

`app_loader.py` используется для динамической загрузки application-модуля.

Цель такой архитектуры — возможность менять команды виртуального устройства во время работы эмулятора, не разрывая существующие TCP-соединения.

## HTTP API

HTTP API слушает только:

```text
127.0.0.1:8000
```

### Logging

Получить состояние traffic logging:

```http
GET /api/logging
```

Включить:

```http
PUT /api/logging
```

Отключить:

```http
PUT /api/logging
```

Параметры API определяются реализацией `api.py`.

Traffic logging используется для диагностики реального обмена UART.

Пример лога:

```text
2026-09-04 14:07:17 INFO uart: client connected: ('10.9.0.1', 49976)
2026-09-04 14:07:21 DEBUG uart: RX ('10.9.0.1', 49976): 68 65 6c 6c 6f 0a
```

### State

Получить текущее состояние:

```http
GET /api/state
```

Пример:

```json
{
  "0x02": -123
}
```

### Events

HTTP API позволяет инжектировать event в подключённых UART-клиентов.

Это используется для тестирования поведения клиентской утилиты при получении событий от устройства.

## Логирование

Логи являются важной частью диагностики.

Используются как минимум следующие логгеры:

```text
uart
uart.protocol
```

Логируются:

* подключение/отключение клиентов;
* входящий traffic;
* исходящий traffic;
* обнаружение `START`;
* обнаружение `STOP`;
* успешно разобранные кадры;
* CRC;
* protocol errors;
* invalid escape;
* timeout;
* garbage;
* ошибки application layer.

Traffic logging можно включать и отключать через HTTP API.

## Тесты

Тесты написаны на `pytest`.

Запустить все:

```bash
make test
```

или:

```bash
.venv/bin/pytest -v t
```

Тесты организованы по задачам:

```text
t/
├── api/
│   ├── test_01_logging.py
│   ├── test_02_logging.py
│   └── ...
│
├── protocol/
│   ├── test_01_good.py
│   ├── test_02_escape.py
│   ├── test_03_errors.py
│   ├── test_04_stream.py
│   └── ...
│
├── uart/
│   ├── test_01_good_frame.py
│   ├── test_02_errors.py
│   ├── test_03_stream.py
│   ├── ...
│   └── test_07_param_02.py
│
├── lib/
│   ├── __init__.py
│   └── uart.py
│
└── test_event.py
```

### Protocol tests

Проверяют непосредственно parser/encoder:

* обычные кадры;
* пустой payload;
* бинарный payload;
* escaping `0x7e`;
* escaping `0x7d`;
* invalid escape;
* короткие кадры;
* bad CRC;
* garbage;
* split frame;
* несколько кадров в одном TCP chunk.

### UART tests

Проверяют уже настоящий TCP UART-сервис:

* обычный request/response;
* ошибки протокола;
* разрыв кадров;
* несколько клиентов;
* команды application layer;
* register read/write;
* datetime;
* event injection.

Для уменьшения дублирования в `t/lib/uart.py` есть высокоуровневые helpers:

```python
uart_command()
uart_get()
uart_set()
```

Поэтому тест команды обычно выглядит примерно так:

```python
await uart_set(reader, writer, 0x02, value)

result = await uart_get(reader, writer, 0x02)

assert result == str(value).encode("ascii")
```

## Makefile

Основные цели:

```text
make init      create venv and install requirements
make req       update requirements.txt
make run       run server
make start     run server in screen
make client    create UART pseudo-terminal using socat
make test      run pytest
```

Для Python-зависимостей используется:

```text
.venv/
requirements.txt
```

`requirements.txt` генерируется через `pip freeze`.

`pkg_resources==0.0.0` не является самостоятельной устанавливаемой зависимостью и не должен попадать в `requirements.txt`.

## Nginx

Внешний доступ к UART HTTP API может проксироваться через nginx.

Типовая схема:

```text
client
   │
   ▼
 nginx
   │
   ├── /uart/      → UART web interface
   └── /uart/api   → 127.0.0.1:8000
```

Сам HTTP application server остаётся доступен только на:

```text
127.0.0.1:8000
```

UART TCP server при этом отдельно слушает:

```text
10.9.0.1:7000
```

## Цели проекта

Основная задача эмулятора — дать реальному UART-клиенту ощущение настоящего устройства:

* клиент подключается к UART и не знает, что это TCP;
* протокол обрабатывается побайтно;
* ошибки протокола воспроизводятся и диагностируются;
* состояние устройства сохраняется;
* команды можно добавлять и изменять без остановки transport layer;
* события можно инжектировать через HTTP API;
* весь обмен можно подробно логировать;
* поведение проверяется автоматическими pytest-тестами.
