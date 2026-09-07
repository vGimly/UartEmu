# UART Emulator

Эмулятор UART-устройства с TCP-интерфейсом, бинарным кадровым протоколом, несколькими версиями протокола, виртуальными устройствами, независимым состоянием устройств и HTTP API для управления и диагностики.

Проект предназначен для разработки и тестирования клиентских UART-утилит без наличия реального устройства BMC.

## Архитектура

```text
                           HTTP API / Web UI
                                  │
                                  ▼
                             ┌──────────┐
                             │ registry │
                             └────┬─────┘
                                  │
             ┌────────────────────┼────────────────────┐
             │                    │                    │
             ▼                    ▼                    ▼
          sessions              devices             protocols
             │                    │                    │
             │                    │                    ▼
             │                    │               app_loader
             │                    │                    │
             │                    └───────┬────────────┘
             │                            │
TCP :7000    │                            ▼
    │        │                       protocol instance
    ▼        │                            │
┌───────────┐│                            ├── client
│  uart.py  │┘                            └── state
└─────┬─────┘
      │
      ▼
┌──────────────┐
│ protocol.py  │
└──────────────┘
```

### Основные компоненты

* `uart.py` — TCP-сервер, управляющий TCP sessions и маршрутизацией команд.
* `protocol.py` — frame parser/encoder, `BaseProtocol`, общие protocol helpers и `ProtocolError`.
* `protocols/` — реализации конкретных версий протоколов. Каждый файл содержит минимальное описание устройства в module docstring.
* `app_loader.py` — inventory, загрузка и создание экземпляров протоколов.
* `registry.py` — связь client sessions и virtual devices, а также управление подключениями и session statistics.
* `state.py` — SQLite-хранилище состояния виртуальных устройств.
* `db.py` — SQLite schema, initialization и migration.
* `api.py` — HTTP API управления эмулятором.
* `templates/` — Web UI.
* `main.py` — запуск HTTP API и UART-сервера.
* `t/` — тесты.

## Virtual devices and client sessions

Эмулятор моделирует набор независимых виртуальных BMC, а не одно глобальное устройство.

Каждое TCP-соединение получает уникальный `client_key`. IP-адрес и TCP-порт являются атрибутами текущей session и не используются как её identity.

```text
TCP connection
      │
      ▼
 client_key
      │
      ▼
 client session
      │
      │ device_id
      ▼
 virtual device
      │
      ├── DEVICE_ID
      ├── protocol
      └── state
```

Поэтому несколько клиентов с одного IP могут одновременно работать с разными виртуальными устройствами:

```text
10.0.0.5:40001 → DEVICE_ID=br850-a → BR850 r0 → state A
10.0.0.5:40002 → DEVICE_ID=br850-b → BR850 r1 → state B
10.0.0.5:40003 → DEVICE_ID=test-a   → another protocol → state C
```

Состояние принадлежит `device_id`, а не TCP session и не protocol module. Поэтому reconnect с тем же `DEVICE_ID` получает состояние соответствующего virtual device.

## Device identification

После подключения клиент может выбрать виртуальное устройство командой `0xFE`.

```text
0xFE <DEVICE_ID in UTF-8>
```

`DEVICE_ID` — UTF-8 строка, идентифицирующая virtual device.

Команда `0xFE` обрабатывается самим `UARTServer` и не передаётся application protocol. После успешной идентификации текущая protocol instance сбрасывается и создаётся заново для выбранного устройства.

Если `DEVICE_ID` неизвестен или payload не является корректным UTF-8, текущая идентичность клиента не изменяется и возвращается `E-*` ошибка.

## Protocol inventory

Все реализации протоколов находятся в `protocols/`.

`app_loader` сканирует эти файлы и извлекает metadata из module docstring без импорта модуля.

Минимальный заголовок протокола:

```python
"""
device: pzbx_br850-r0
version: 1.0.1
description: PZBX BR850 protocol revision 0
"""
```

Таким образом, доступные устройства и версии протокола автоматически определяются по содержимому `protocols/`.

Общие protocol helpers находятся в `protocol.py`, поэтому файлы в `protocols/` содержат только implementation details конкретного протокола.

## Protocol classes

Каждый protocol instance привязан к одной client session и получает client context и общее state storage:

```python
class BaseProtocol:
    def __init__(self, client, state):
        self.client = client
        self.state = state
```

Конкретный протокол реализует:

```python
class Protocol(BaseProtocol):
    def command(self, cmd, payload):
        ...
```

Внутри протокола доступны:

```python
self.client
self.state
self.register_read_write(...)
```

без передачи `client` отдельным аргументом в каждую функцию.

## Errors

Ошибки application protocol не кодируются отрицательными числовыми значениями. Они представлены исключением `ProtocolError` и превращаются UART server в текстовый результат с префиксом `E-`.

Например:

```python
raise ProtocolError("INVALID_VALUE")
```

возвращает:

```text
E-INVALID_VALUE
```

Это позволяет использовать отрицательные значения регистров как обычные данные.

Ошибки кадрового уровня имеют отдельные числовые коды:

```text
0x80  timeout
0x81  short frame
0x82  bad CRC
0x83  invalid escape
0x84  garbage before start
```

Они возвращаются как кадр с командой `0xFF`.

## Session statistics

Для каждой client session ведутся:

* `client_key`;
* source host and port;
* connection status;
* `connected_at`;
* текущая длительность session;
* `requests`;
* `responses`;
* `first_seen` / `last_seen`;
* выбранный `device` и `DEVICE_ID`;
* выбранный protocol.

Счётчики `requests` и `responses` относятся к конкретной TCP session и не агрегируются по IP.

Web UI показывает текущие sessions, назначенные devices, protocol и state, а также время подключения, длительность и счётчики request/response.

## SQLite model

Основные сущности:

```text
clients
  client_key
  host
  port
  device_id
  connected
  connected_at
  requests
  responses

        │
        │ device_id
        ▼

devices
  id
  identity
  name
  protocol
  description

        │
        │ device_id
        ▼

state
  device_id
  address
  value
```

`state` имеет составной ключ `(device_id, address)`, поэтому одинаковый register address может иметь разные значения на разных виртуальных устройствах.

Database initialization/migration выполняется через `db.py`.

## State API and Web UI

Состояние виртуального устройства доступно непосредственно через API:

```text
GET    /api/devices/{device_id}/state
PUT    /api/devices/{device_id}/state/{address}
DELETE /api/devices/{device_id}/state/{address}
DELETE /api/devices/{device_id}/state
```

`PUT` создаёт новую запись или изменяет существующую, `DELETE` удаляет отдельный register, а удаление collection очищает всё состояние устройства.

Для просмотра состояния используется страница:

```text
/devices/{device_id}
```

Dashboard содержит ссылку `Open state` для каждого virtual device. На странице устройства доступны просмотр, запись, удаление отдельных register и очистка всего state.

## Запуск

Проект использует Python virtual environment.

Создание окружения и установка зависимостей:

```bash
make init
```

После добавления новых Python packages также необходимо выполнить:

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

## Web UI and API

Web UI доступен по корневому HTTP endpoint приложения.

Swagger UI сохраняется по адресу `/docs` и используется для интерактивного просмотра и тестирования API.

Web UI предназначен для наблюдения за текущим состоянием emulator model: sessions, devices, protocols и state.

## UART client

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

## Protocol framing

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

CRC вычисляется по исходным данным кадра до escaping согласно реализации `protocol.py`.

CRC передаётся двумя байтами.

## Development

Рабочая ветка разработки:

```text
redesign/dev-mgmt
```

Перед запуском тестов после изменения зависимостей:

```bash
make init
```

Тесты запускаются через pytest.

Новые protocol implementations должны находиться в `protocols/`, содержать metadata docstring и наследовать `BaseProtocol` через экспорт класса `Protocol`.
