import uuid


class TraceID:
    _id = uuid.uuid4()

    @classmethod
    def reset(cls) -> None:
        cls._id = uuid.uuid4()

    @classmethod
    def id(cls) -> uuid.UUID:
        return cls._id
