# resource_manager.py
from PyQt5.QtCore import QObject, pyqtSignal, QThreadPool, QRunnable, QMetaObject, Qt, pyqtSlot, Q_ARG
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

    def __init__(self, agent, max_threads=2, max_memory_gb=None, max_memory_ratio=0.25):
        super().__init__()
        self.agent = agent
        self.max_threads = max_threads

        # Calcul automatique de max_memory_gb si non fourni
        total_ram_gb = psutil.virtual_memory().total / (1024 ** 3)
        if max_memory_gb is None:
            self.max_memory_gb = total_ram_gb * max_memory_ratio
        else:
            self.max_memory_gb = max_memory_gb

        self.max_memory_bytes = self.max_memory_gb * (1024 ** 3)
        self.thread_pool = QThreadPool()
        self.thread_pool.setMaxThreadCount(self.max_threads)
        self.mutex = threading.Lock()

        print(f"[INFO] IAResourceManager initialisé avec seuil RAM disponible minimal de {self.max_memory_gb:.2f} GB (total RAM={total_ram_gb:.2f} GB)")

    @pyqtSlot(str)
    def emit_overload_signal(self, message):
        self.overload_signal.emit(message)

    @pyqtSlot()
    def emit_ready_signal(self):
        self.ready_signal.emit()

    def can_run(self):
        cpu_usage = psutil.cpu_percent(interval=0.1)
        ram_available = psutil.virtual_memory().available
        ram_available_gb = ram_available / (1024 ** 3)

        print(f"[DEBUG] can_run(): CPU={cpu_usage:.1f}%, RAM disponible={ram_available_gb:.2f}GB, seuil RAM={self.max_memory_gb:.2f}GB")

        # Tolérance 90% du seuil mémoire
        ram_seuil_tolerance = self.max_memory_bytes * 0.9

        if cpu_usage > 85 or ram_available < ram_seuil_tolerance:
            message = f"Surcharge détectée : CPU={cpu_usage}%, RAM disponible={ram_available_gb:.2f}GB (seuil tolérance: {ram_seuil_tolerance/(1024**3):.2f}GB)"
            QMetaObject.invokeMethod(self, "emit_overload_signal", Qt.QueuedConnection, Q_ARG(str, message))
            return False

        QMetaObject.invokeMethod(self, "emit_ready_signal", Qt.QueuedConnection)
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
        ram_available_gb = psutil.virtual_memory().available / (1024 ** 3)

        if cpu > 85 or ram_available_gb < self.max_memory_gb:
            message = f"[ALERTE] CPU={cpu:.1f}%, RAM disponible={ram_available_gb:.2f}GB"
            print(message)
            QMetaObject.invokeMethod(self, "emit_overload_signal", Qt.QueuedConnection, Q_ARG(str, message))
            return False
        return True
