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
    overload_signal = pyqtSignal(str)
    ready_signal = pyqtSignal()

    _instance = None  # Singleton
    _initialized = False

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(IAResourceManager, cls).__new__(cls)
        return cls._instance

    def __init__(self, agent=None, max_threads=2, max_memory_gb=None, max_memory_ratio=0.25):
        if self._initialized:
            return
        super().__init__()

        self.agent = agent
        self.max_threads = max_threads
        total_ram_gb = psutil.virtual_memory().total / (1024 ** 3)
        self.max_memory_gb = max_memory_gb if max_memory_gb is not None else total_ram_gb * max_memory_ratio
        self.max_memory_bytes = self.max_memory_gb * (1024 ** 3)

        self.thread_pool = QThreadPool()
        self.thread_pool.setMaxThreadCount(self.max_threads)
        self.mutex = threading.Lock()

        print(f"[INFO] IAResourceManager initialisé avec seuil RAM disponible minimal de {self.max_memory_gb:.2f} GB (total RAM={total_ram_gb:.2f} GB)")

        self._initialized = True

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

        marge_securite_gb = 0.5
        seuil_effectif_gb = self.max_memory_gb + marge_securite_gb
        seuil_effectif_bytes = seuil_effectif_gb * (1024 ** 3)

        print(f"[DEBUG] can_run(): CPU={cpu_usage:.1f}%, RAM disponible={ram_available_gb:.2f}GB, seuil RAM={seuil_effectif_gb:.2f}GB")

        if cpu_usage > 85 or ram_available < seuil_effectif_bytes:
            message = f"Surcharge détectée : CPU={cpu_usage:.1f}%, RAM disponible={ram_available_gb:.2f}GB < seuil {seuil_effectif_gb:.2f}GB"
            QMetaObject.invokeMethod(self, "emit_overload_signal", Qt.QueuedConnection, Q_ARG(str, message))
            return False

        QMetaObject.invokeMethod(self, "emit_ready_signal", Qt.QueuedConnection)
        return True

    def submit(self, fn, *args, **kwargs):
        if not self.can_run():
            print("[SUBMIT] Refusé par can_run() — ressources insuffisantes.")
            return False
        print("[SUBMIT] Requête acceptée — exécution dans le thread pool.")
        runnable = IARunnable(fn, *args, **kwargs)
        self.thread_pool.start(runnable)
        return True

    def stop(self):
        self.thread_pool.clear()
        self.thread_pool.waitForDone()

    def ressources_disponibles(self):
        cpu = psutil.cpu_percent(interval=0.5)
        ram_available = psutil.virtual_memory().available
        ram_available_gb = ram_available / (1024 ** 3)

        marge_securite_gb = 0.5
        seuil_effectif_gb = self.max_memory_gb + marge_securite_gb
        seuil_effectif_bytes = seuil_effectif_gb * (1024 ** 3)

        if cpu > 85 or ram_available < seuil_effectif_bytes:
            message = f"[ALERTE] CPU={cpu:.1f}%, RAM disponible={ram_available_gb:.2f}GB < seuil {seuil_effectif_gb:.2f}GB"
            print(message)
            QMetaObject.invokeMethod(self, "emit_overload_signal", Qt.QueuedConnection, Q_ARG(str, message))
            return False
        return True

    def update_config(self, *, agent=None, max_threads=None, max_memory_gb=None, max_memory_ratio=None):
        if agent is not None:
            self.agent = agent
            print("[CONFIG] Agent mis à jour.")

        if max_threads is not None:
            self.max_threads = max_threads
            self.thread_pool.setMaxThreadCount(max_threads)
            print(f"[CONFIG] max_threads mis à jour : {max_threads}")

        if max_memory_gb is not None:
            self.max_memory_gb = max_memory_gb
            self.max_memory_bytes = max_memory_gb * (1024 ** 3)
            print(f"[CONFIG] max_memory_gb mis à jour : {max_memory_gb:.2f} GB")

        elif max_memory_ratio is not None:
            total_ram_gb = psutil.virtual_memory().total / (1024 ** 3)
            self.max_memory_gb = total_ram_gb * max_memory_ratio
            self.max_memory_bytes = self.max_memory_gb * (1024 ** 3)
            print(f"[CONFIG] max_memory_ratio appliqué : {max_memory_ratio:.2f}, soit {self.max_memory_gb:.2f} GB")
