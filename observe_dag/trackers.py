import json
import pathlib
import pkgutil
import sys
from typing import Optional, Any, Callable, Iterator

from importlib.metadata import version, PackageNotFoundError


from observe_dag.protocols import FrameProtocol
from observe_dag.stack_element import StackElement, NotIncludedError
from observe_dag.stack_trace import NodeStack
from observe_dag.stacks import TrainStack, InferStack, ProcessingStack
from observe_dag.trace_id import TraceID
from observe_dag.tracking_type import TrackingType


class Observer:
    _type: Optional[TrackingType] = None
    _previous_tracking_fn: Optional[Callable] = None
    _relevant_tracker: Optional[NodeStack] = None

    @classmethod
    def is_active(cls) -> bool:
        return cls._relevant_tracker is not None

    @classmethod
    def track(cls, tracking_type: TrackingType) -> None:
        if cls.is_active():
            cls.stop()
        cls._type = tracking_type
        cls._previous_tracking_fn = sys.gettrace()

        if tracking_type == TrackingType.Training:
            cls._relevant_tracker = TrainStack
        elif tracking_type == TrackingType.Inference:
            cls._relevant_tracker = InferStack
        elif tracking_type == TrackingType.Processing:
            cls._relevant_tracker = ProcessingStack
        else:
            raise RuntimeError(f"Unknown Stack Type {tracking_type}")

        def tracking_fn(
                frame: Optional[FrameProtocol], event: str, arg_frame: Optional[Any]
        ):
            if event == "call" and frame is not None:
                try:
                    cls._relevant_tracker.add_node(StackElement.from_frame(frame))
                except NotIncludedError:
                    pass
            if cls._previous_tracking_fn is not None:
                cls._previous_tracking_fn(frame, event, arg_frame)

        sys.settrace(tracking_fn)

    @staticmethod
    def _loaded_libraries() -> Iterator[tuple[str, str]]:
        installed_packages = list(pkgutil.iter_modules())
        for module in installed_packages:
            try:
                yield module.name, version(module.name)
            except PackageNotFoundError:
                pass

    @classmethod
    def save_libraries(cls) -> None:
        library_dest = (
                pathlib.Path.home()
                / ".stack_traces"
                / str(TraceID.id())
                / "versions.txt"
        )
        if not library_dest.exists():
            with open(library_dest, 'w') as f:
                json.dump(dict(cls._loaded_libraries()), f)

    @classmethod
    def stop(cls) -> None:
        cls._type = None
        cls._relevant_tracker.dump()
        cls.save_libraries()
        cls._relevant_tracker = None
        sys.settrace(cls._previous_tracking_fn)
        cls._previous_tracking_fn = None
