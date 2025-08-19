# system_monitor.py (Version finale améliorée)

import psutil
import torch
import time
import threading
import onnxruntime as ort

class SystemMonitor:
    def __init__(self):
        self.gpu_available = torch.cuda.is_available()
        self.nvml_available = False
        self.nvml = None
        self.gpu_handle = None

        self._metrics = {
            'cpu_usage': 0.0,
            'gpu_usage': 0.0,
            'gpu_memory_used': 0.0,
            'memory_usage': 0.0
        }
        self._running = False
        
        self._setup_onnx_providers()
        self._init_nvml()
        self._start_monitoring()

    def _setup_onnx_providers(self):
        """Détermine les meilleurs providers ONNX Runtime disponibles."""
        self.onnx_providers = []
        available_providers = ort.get_available_providers()
        
        if self.gpu_available and 'CUDAExecutionProvider' in available_providers:
            self.onnx_providers.append('CUDAExecutionProvider')
        
        self.onnx_providers.append('CPUExecutionProvider')
        print(f"✅ System monitor configured ONNX providers: {self.onnx_providers}")

    def _init_nvml(self):
        """Initialise la bibliothèque NVML pour une surveillance GPU précise."""
        if not self.gpu_available:
            print("ℹ️ GPU not available, GPU monitoring is disabled.")
            return

        try:
            import pynvml
            pynvml.nvmlInit()
            self.nvml = pynvml
            self.gpu_handle = self.nvml.nvmlDeviceGetHandleByIndex(0)
            self.nvml_available = True
            print("✅ NVML initialized for GPU monitoring.")
        except ImportError:
             print("❌ ERROR: The 'pynvml' library is not installed. Run 'pip install pynvml'.")
             self.nvml_available = False
        except Exception as e:
            # Affiche une erreur beaucoup plus détaillée !
            print(f"❌ CRITICAL ERROR: NVML could not be initialized. GPU metrics will be 0.")
            print(f"   Probable reason: Issue with NVIDIA drivers or permissions.")
            print(f"   Original error message: {e}")
            self.nvml_available = False

    def _start_monitoring(self):
        """Démarre le thread de surveillance en arrière-plan."""
        # Fait une première lecture immédiate pour éviter d'afficher des 0 au début
        self._update_all_metrics()
        
        self._running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        
    def _update_all_metrics(self):
        """Méthode unique pour mettre à jour toutes les métriques en une fois."""
        # --- CORRECTION CPU ---
        # Utilise un intervalle pour une mesure correcte
        self._metrics['cpu_usage'] = psutil.cpu_percent(interval=0.5)
        self._metrics['memory_usage'] = psutil.virtual_memory().percent

        # Métriques GPU
        if self.nvml_available and self.gpu_handle:
            try:
                utilization = self.nvml.nvmlDeviceGetUtilizationRates(self.gpu_handle)
                self._metrics['gpu_usage'] = float(utilization.gpu)

                mem_info = self.nvml.nvmlDeviceGetMemoryInfo(self.gpu_handle)
                self._metrics['gpu_memory_used'] = (mem_info.used / mem_info.total) * 100 if mem_info.total > 0 else 0.0
            except Exception:
                self._metrics['gpu_usage'] = 0.0
                self._metrics['gpu_memory_used'] = 0.0
        else:
            # Si NVML a échoué, on met explicitement à 0
            self._metrics['gpu_usage'] = 0.0
            self._metrics['gpu_memory_used'] = 0.0

    def _monitor_loop(self):
        """Boucle qui met à jour les métriques système périodiquement."""
        psutil.cpu_percent(interval=None)
        time.sleep(1)
        while self._running:
            # Utilise un intervalle pour une mesure correcte
            self._metrics['cpu_usage'] = psutil.cpu_percent(interval=None) # Non-blocking
            self._metrics['memory_usage'] = psutil.virtual_memory().percent
            if self.nvml_available and self.gpu_handle:
                try:
                    utilization = self.nvml.nvmlDeviceGetUtilizationRates(self.gpu_handle)
                    self._metrics['gpu_usage'] = float(utilization.gpu)
                    mem_info = self.nvml.nvmlDeviceGetMemoryInfo(self.gpu_handle)
                    self._metrics['gpu_memory_used'] = (mem_info.used / mem_info.total) * 100 if mem_info.total > 0 else 0.0
                except Exception:
                    self._metrics['gpu_usage'] = 0.0
                    self._metrics['gpu_memory_used'] = 0.0
            
            time.sleep(1) # Met à jour toutes les secondes

    def get_metrics(self):
        """Retourne une copie des dernières métriques collectées."""
        return self._metrics.copy()

    def __del__(self):
        """Nettoie les ressources à la destruction de l'objet."""
        self._running = False
        if self.nvml_available:
            try:
                self.nvml.nvmlShutdown()
            except:
                pass

# Instance globale unique qui sera importée partout
system_monitor = SystemMonitor()