from observe_dag.stack_trace import NodeStack
from observe_dag.tracking_type import TrackingType

TrainStack = NodeStack(TrackingType.Training)
InferStack = NodeStack(TrackingType.Inference)
ProcessingStack = NodeStack(TrackingType.Processing)
