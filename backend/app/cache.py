"""Tiny in-process cache for expensive read models (the network graph). Every audited action bumps the version,
which drops everything, so a cached answer can never outlive a change to the records it was built from."""
_version = 0
_store: dict = {}


def bump() -> None:
    global _version
    _version += 1
    _store.clear()


def memo(key: tuple, build):
    k = (key, _version)
    if k not in _store:
        _store[k] = build()
    return _store[k]
