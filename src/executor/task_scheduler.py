import queue
import threading
import time
import logging

logger = logging.getLogger(__name__)

class TaskScheduler:
    def __init__(self):
        self.task_queue = queue.Queue()
        self.is_running = False

    def add_task(self, task_func, *args, **kwargs):
        self.task_queue.put((task_func, args, kwargs))

    def start(self):
        self.is_running = True
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        while self.is_running:
            try:
                task_func, args, kwargs = self.task_queue.get(timeout=1)
                task_func(*args, **kwargs)
                self.task_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Error executing task: {e}")

    def stop(self):
        self.is_running = False
