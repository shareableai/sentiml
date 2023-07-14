from sentiml.stack_trace import NodeStack
from sentiml.tracking_type import TrackingType

TrainStack = NodeStack(TrackingType.Training)
InferStack = NodeStack(TrackingType.Inference)
ProcessingStack = NodeStack(TrackingType.Processing)
