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

# name -> imported module object, cached so repeated commands don't
# re-import, and so reload() can find the right module to reload.
_modules = {}


def _module_path(protocol):
    return os.path.join(PROTOCOLS_DIR, protocol + ".py")


def _load(protocol):
    if protocol in _modules:
        return _modules[protocol]

    module = importlib.import_module("%s.%s" % (PROTOCOLS_PACKAGE, protocol))
    _modules[protocol] = module

    return module


def validate_protocol(protocol):
    try:
        _load(protocol)
    except ImportError:
        return False

    return True


def reload(protocol=None):
    """
    Reload one protocol module, or all previously loaded ones when
    `protocol` is None.
    """

    importlib.invalidate_caches()

    if protocol is None:
        for module in _modules.values():
            importlib.reload(module)
        return

    module = _load(protocol)
    importlib.reload(module)


def command(protocol, client, cmd, payload):
    try:
        module = _load(protocol)
    except ImportError:
        log.error("unknown protocol module: %s", protocol)
        return None

    return module.command(client, cmd, payload)


def dump_state(protocol="default"):
    module = _load(protocol)

    return module.state.dump()


def _read_header(path):
    """
    Read `device` / `version` / `description` from the module's
    docstring, WITHOUT importing (and therefore executing) the file.

    Expected header format, as the first statement in the file:

        \"\"\"
        device: pzbx_br850-r0
        version: 1.0.1
        description: short human description
        \"\"\"

    Only what's declared here is trusted. The filename is just an
    import handle (and must be a valid Python identifier, so it can't
    even carry things like hyphens) -- never a source of metadata.
    """

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
    """
    Discover protocol modules by scanning protocols/ on disk. Each
    file's metadata is parsed from its header (see _read_header) --
    modules are never imported just to build this listing.
    """

    protocols = []

    if not os.path.isdir(PROTOCOLS_DIR):
        return protocols

    for filename in sorted(os.listdir(PROTOCOLS_DIR)):
        if not filename.endswith(".py") or filename.startswith("_"):
            continue

        module_name = filename[:-3]
        metadata = _read_header(_module_path(module_name))

        protocols.append(
            {
                "module": module_name,
                **metadata,
            }
        )

    return protocols
