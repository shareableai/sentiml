import json
import atexit

from observer.trace_id import TraceID
from weaver.weave import weave

from uuid import uuid4

from typing import TypeVar, Optional
from functools import partial

T = TypeVar('T')


def track_class(item: T, class_name: Optional[str] = None) -> T:
    if (existing_class_name := getattr(item, '__observer_class_name__', None)) is not None:
        inner_class_name = existing_class_name
    elif class_name is not None:
        inner_class_name = class_name
    else:
        inner_class_name = str(uuid4())
    try:
        setattr(item, '__observer_class_name__', inner_class_name)
    except BaseException:
        # It's nice to have a consistent name for an object, but it's fairly trivial.
        pass
    def teardown(self):
        # Remove teardown function from class
        setattr(self, '__teardown__', None)
        res: dict = weave(self).as_dict()
        root_dir = TraceID.root_dir() / 'classes'
        root_dir.mkdir(exist_ok=True, parents=True)
        with open(root_dir / f"{inner_class_name}.json", 'w') as f:
            json.dump(res, f)
        
    setattr(item, '__teardown__', teardown)
    atexit.register(partial(item.__teardown__, self=item))
