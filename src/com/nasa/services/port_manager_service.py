import logging
import threading
import time
from dataclasses import dataclass
from typing import Dict, Optional, List

from com.nasa.infra.serial.port_probe import ProbeConfig, list_candidate_ports, probe_imei
from com.nasa.services.sms_service import SmsService

# logger = logging.getLogger("com.nasa.services.PortManagerService")

@dataclass
class WorkerHandle:
    imei: str
    port: str
    thread: threading.Thread

class PortManagerService:
    logger = logging.getLogger(__name__)
    def __init__(self,
                 manual_ports: Optional[List[str]],
                 baudrate: int,
                 scan_interval_s: float,
                 probe_timeout_s: float,
                 serial_timeout_s: float,
                 poll_interval_s: float,
                 sms_service_factory):
        self.manual_ports = manual_ports
        self.baudrate = baudrate
        self.scan_interval_s = scan_interval_s
        self.probe_timeout_s = probe_timeout_s
        self.serial_timeout_s = serial_timeout_s
        self.poll_interval_s = poll_interval_s
        self.sms_service_factory = sms_service_factory
        self._stop_event = threading.Event()
        self.probe_cfg = ProbeConfig(baudrate=baudrate, timeout_seconds=probe_timeout_s)
        self.workers: Dict[str, WorkerHandle] = {}

    def stop(self) -> None:
        """Request PortManager to stop gracefully."""
        self._stop_event.set()

    def run_forever(self) -> None:
        self.logger.info("started manual_ports=%s baud=%s scan=%ss probe_timeout=%ss",
                    self.manual_ports, self.baudrate, self.scan_interval_s, self.probe_timeout_s)

        while not self._stop_event.is_set():
            dead = [imei for imei, h in self.workers.items() if not h.thread.is_alive()]
            for imei in dead:
                self.logger.warning("worker dead imei=%s (was port=%s)", imei, self.workers[imei].port)
                self.workers.pop(imei, None)

            ports = list_candidate_ports(self.manual_ports)
            busy_ports = {h.port for h in self.workers.values()}
            candidates = [p for p in ports if p not in busy_ports]
            self.logger.info("candidate ports=%s (all=%s busy=%s)",candidates,ports,busy_ports),
            for port in candidates:
                
                imei = probe_imei(port, self.probe_cfg)
                if not imei:
                    self.logger.debug("port not sim: %s", port)
                    continue
                if imei in self.workers:
                    self.logger.debug("port in use: %s, imei: %s", port, imei)
                    continue

                service: SmsService = self.sms_service_factory(port, imei)
                t = threading.Thread(target=service.run_forever, name=f"worker-{imei}", daemon=True)

                self.workers[imei] = WorkerHandle(imei=imei, port=port, thread=t)
                t.start()
                self.logger.info("spawned worker imei=%s port=%s", imei, port)

            time.sleep(self.scan_interval_s)
        self.logger.info("stopped")
