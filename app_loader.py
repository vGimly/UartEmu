import importlib
import application


def reload():
    importlib.invalidate_caches()
    importlib.reload(application)


def command(client, cmd, payload):
    return application.command(client, cmd, payload)


def dump_state():
    return application.state.dump()
