import uuid
import pathlib


class TraceID:
    _id = uuid.uuid4()

    @classmethod
    def reset(cls) -> None:
        cls._id = uuid.uuid4()

    @classmethod
    def id(cls) -> uuid.UUID:
        return cls._id
    
    @classmethod
    def root_dir(cls) -> pathlib.Path:
        root_dir = (
                pathlib.Path.home()
                / ".stack_traces"
                / str(TraceID.id())
        )
        root_dir.mkdir(parents=True, exist_ok=True)
        return root_dir