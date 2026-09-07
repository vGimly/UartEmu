import ast
import importlib
import logging
import os

log = logging.getLogger("uart.app_loader")

PROTOCOLS_PACKAGE = "protocols"
PROTOCOLS_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    PROTOCOLS_PACKAGE,
)

_modules = {}


def _module_path(protocol):
    return os.path.join(PROTOCOLS_DIR, protocol + ".py")


def _load(protocol):
    if protocol in _modules:
        return _modules[protocol]

    module = importlib.import_module("%s.%s" % (PROTOCOLS_PACKAGE, protocol))
    _modules[protocol] = module
    return module


def _create(protocol, client):
    module = _load(protocol)
    return module.Protocol(client)


def validate_protocol(protocol):
    try:
        module = _load(protocol)
    except ImportError:
        return False
    return hasattr(module, "Protocol")


def reload(protocol=None):
    importlib.invalidate_caches()

    if protocol is None:
        for module in _modules.values():
            importlib.reload(module)
        return

    module = _load(protocol)
    importlib.reload(module)


def command(protocol, client, cmd, payload):
    try:
        instance = _create(protocol, client)
    except ImportError:
        log.error("unknown protocol module: %s", protocol)
        return None

    return instance.command(cmd, payload)


def dump_state(protocol, device_id):
    module = _load(protocol)
    instance = module.Protocol({"device_id": device_id})
    if instance.state is None or device_id is None:
        return {}
    return instance.state.dump(device_id)


def clear_state(protocol, device_id):
    try:
        module = _load(protocol)
    except ImportError:
        return

    instance = module.Protocol({"device_id": device_id})
    if instance.state is not None and device_id is not None:
        instance.state.clear(device_id)
        log.info(
            "cleared state: device=%s protocol=%s",
            device_id,
            protocol,
        )


def _read_header(path):
    """Read protocol metadata from the module docstring without importing it."""
    metadata = {"device": None, "version": None, "description": None}

    try:
        with open(path, "r", encoding="utf-8") as f:
            source = f.read()
        tree = ast.parse(source, filename=path)
        docstring = ast.get_docstring(tree)
    except (OSError, SyntaxError, UnicodeDecodeError) as exc:
        log.warning("could not read header of %s: %s", path, exc)
        return metadata

    if not docstring:
        return metadata

    for line in docstring.splitlines():
        line = line.strip()
        if not line or ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip().lower()
        if key in metadata:
            metadata[key] = value.strip()

    return metadata


def list_protocols():
    protocols = []

    if not os.path.isdir(PROTOCOLS_DIR):
        return protocols

    for filename in sorted(os.listdir(PROTOCOLS_DIR)):
        if not filename.endswith(".py") or filename.startswith("_"):
            continue

        module_name = filename[:-3]
        protocols.append(
            {
                "module": module_name,
                **_read_header(_module_path(module_name)),
            }
        )

    return protocols
