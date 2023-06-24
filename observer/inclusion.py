from typing import Optional

from observer.default_libraries import DEFAULT_LIBS, DEV_LIBS, LIBS_THAT_ARENT_RELEVANT


def should_include_module(module: Optional[str]) -> bool:
    return (module is not None
            and module != "UnknownModule"
            and next(iter(module.split("."))) not in DEFAULT_LIBS
            and next(iter(module.split("."))) not in DEV_LIBS
            and not any([lib in module for lib in LIBS_THAT_ARENT_RELEVANT])
            )
