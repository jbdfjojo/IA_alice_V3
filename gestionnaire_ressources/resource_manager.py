# resource_manager.py
from PyQt5.QtCore import QObject, pyqtSignal, QThreadPool, QRunnable, QMetaObject, Qt
import psutil
import threading

class IARunnable(QRunnable):
    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs

    def run(self):
        self.fn(*self.args, **self.kwargs)

class IAResourceManager(QObject):
    overload_signal = pyqtSignal(str)  # Signal en cas de surcharge CPU/RAM
    ready_signal = pyqtSignal()        # Signal quand ressources OK

    def __init__(self, agent, max_threads=2, max_memory_gb=4):
        super().__init__()
        self.agent = agent
        self.max_threads = max_threads
        self.max_memory_gb = max_memory_gb
        self.max_memory_bytes = max_memory_gb * (1024 ** 3)
        self.thread_pool = QThreadPool()
        self.thread_pool.setMaxThreadCount(self.max_threads)
        self.mutex = threading.Lock()

    def can_run(self):
        cpu_usage = psutil.cpu_percent(interval=0.1)
        ram_usage = psutil.virtual_memory().used
        if cpu_usage > 85 or ram_usage > self.max_memory_bytes:
            message = f"Surcharge détectée : CPU={cpu_usage}%, RAM={ram_usage / (1024**3):.2f}GB"
            QMetaObject.invokeMethod(self, lambda: self.overload_signal.emit(message), Qt.QueuedConnection)
            return False
        QMetaObject.invokeMethod(self, "ready_signal", Qt.QueuedConnection)
        return True

    def submit(self, fn, *args, **kwargs):
        if not self.can_run():
            return False
        runnable = IARunnable(fn, *args, **kwargs)
        self.thread_pool.start(runnable)
        return True

    def stop(self):
        self.thread_pool.clear()
        self.thread_pool.waitForDone()

    def ressources_disponibles(self):
        cpu = psutil.cpu_percent(interval=0.5)
        mem_gb = psutil.virtual_memory().used / (1024 ** 3)

        if cpu > 85 or mem_gb > self.max_memory_gb:
            message = f"[ALERTE] CPU={cpu:.1f}%, RAM={mem_gb:.2f}GB"
            print(message)
            QMetaObject.invokeMethod(self, lambda: self.overload_signal.emit(message), Qt.QueuedConnection)
            return False
        return True
