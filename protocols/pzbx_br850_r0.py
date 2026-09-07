"""
device: pzbx_br850-r0
version: 1.0.1
description: Протокол для PZBX BR850 rev.0 — идентификация модели и эхо-тест.
"""

# Имя файла (pzbx_br850_r0.py) — это просто идентификатор модуля Python
# (дефисы там недопустимы). Настоящая модель устройства, версия
# прошивки/протокола и описание берутся ТОЛЬКО из заголовка выше —
# по имени файла ничего не угадывается.


def command(client, cmd, payload):
    if cmd == 0x01:
        return b"OK=" + payload

    if cmd == 0x20:
        return b"pzbx_br850-r0"

    return None
