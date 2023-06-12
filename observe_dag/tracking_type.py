from enum import Enum, auto


class TrackingType(Enum):
    Processing = auto()
    Training = auto()
    Inference = auto()
