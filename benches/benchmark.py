import time
from observe_dag.stack_trace import NodeStack


def f():
    return True


if __name__ == "__main__":
    now = time.time()
    for _ in range(10_000):
        _ = f()
    diff = time.time() - now

    trace_now = time.time()
    for _ in range(10_000):
        _ = f()
    trace_diff = time.time() - now

    print(f"{now=}, {trace_now} ({trace_diff}=)")
