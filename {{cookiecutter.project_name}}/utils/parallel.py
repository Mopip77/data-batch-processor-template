from concurrent.futures import ThreadPoolExecutor
from functools import wraps
import threading
from typing import Iterable, List, Optional


class FutureProxy:
    def __init__(self, fut):
        self._f = fut

    def join(self, timeout: Optional[float] = None):
        return self._f.result(timeout=timeout)

    def result(self, timeout: Optional[float] = None):
        return self._f.result(timeout=timeout)

    def exception(self, timeout: Optional[float] = None):
        return self._f.exception(timeout=timeout)

    def done(self) -> bool:
        return self._f.done()

    def add_done_callback(self, fn):
        return self._f.add_done_callback(fn)


def parallel(pool_size: int = 5):
    """Decorator to run function calls in a thread pool and return joinable futures.

    Usage:
        @parallel(pool_size=5)
        def handle_one_task(row):
            ...
            return result

        futures = [handle_one_task(row) for _, row in df.iterrows()]
        results = [f.join() for f in futures]
        handle_one_task.pool_shutdown()
    """

    def decorator(func):
        executor = None
        lock = threading.Lock()

        def _ensure_executor():
            nonlocal executor
            if executor is None:
                with lock:
                    if executor is None:
                        executor = ThreadPoolExecutor(max_workers=pool_size, thread_name_prefix=f"parallel-{func.__name__}")
            return executor

        @wraps(func)
        def wrapper(*args, **kwargs):
            ex = _ensure_executor()
            fut = ex.submit(func, *args, **kwargs)
            return FutureProxy(fut)

        def pool_shutdown(wait: bool = True):
            nonlocal executor
            if executor is not None:
                executor.shutdown(wait=wait)
                executor = None

        wrapper.pool_shutdown = pool_shutdown
        return wrapper

    return decorator


def join_all(futures: Iterable[FutureProxy]) -> List:
    return [f.join() for f in futures]

