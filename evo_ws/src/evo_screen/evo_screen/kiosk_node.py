"""Node ROS minimal : affiche la page /kiosk en plein écran sur le LCD du robot.

Remplace l'ancien rendu LCD Pillow piloté par /reception/qr/status. Désormais l'écran
affiche directement le kiosk web (camera + scan + écrans gérés par l'app Laravel), depuis
une IP passée en paramètre.

    ros2 run evo_screen kiosk --ros-args -p host:=10.10.221.104
"""

import os
import shutil
import subprocess

import rclpy
from rclpy.node import Node

from evo_screen.kiosk_cmd import build_chromium_args, build_origin, build_url, find_chromium


class KioskNode(Node):
    def __init__(self):
        super().__init__("kiosk_screen")

        self.declare_parameter("host", "")
        self.declare_parameter("port", 80)
        self.declare_parameter("path", "/kiosk")
        self.declare_parameter("display", ":0")
        self.declare_parameter("profile", "/tmp/kiosk-chrome")
        self.declare_parameter("disable_gpu", False)
        self.declare_parameter("secure_origin", True)

        host = self.get_parameter("host").get_parameter_value().string_value.strip()
        port = self.get_parameter("port").get_parameter_value().integer_value
        path = self.get_parameter("path").get_parameter_value().string_value
        self._display = self.get_parameter("display").get_parameter_value().string_value
        self._profile = self.get_parameter("profile").get_parameter_value().string_value
        disable_gpu = self.get_parameter("disable_gpu").get_parameter_value().bool_value
        secure_origin = self.get_parameter("secure_origin").get_parameter_value().bool_value

        self._proc = None
        self._chrome = None
        self._shutting_down = False

        if not host:
            self.get_logger().error(
                "Paramètre 'host' vide. Lance avec : "
                "ros2 run evo_screen kiosk --ros-args -p host:=<ip-laptop>"
            )
            return

        self._chrome = find_chromium()
        if not self._chrome:
            self.get_logger().error(
                "Aucun binaire chromium/chrome trouvé. "
                "Installer : sudo apt-get install -y chromium-browser"
            )
            return

        self._url = build_url(host, port, path)
        self._origin = build_origin(host, port) if secure_origin else None
        self._disable_gpu = disable_gpu

        self._launch()
        # Filet de résilience : un kiosk doit rester affiché → relance chromium s'il meurt.
        self._timer = self.create_timer(2.0, self._watchdog)

    def _env(self):
        env = dict(os.environ)
        env["DISPLAY"] = self._display or ":0"
        return env

    def _launch(self):
        # Profil neuf (requis pour le flag secure-origin) + autorise les clients X locaux.
        shutil.rmtree(self._profile, ignore_errors=True)
        try:
            subprocess.run(
                ["xhost", "+local:"], env=self._env(),
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False,
            )
        except FileNotFoundError:
            pass

        args = build_chromium_args(
            self._chrome, self._url,
            profile=self._profile, origin=self._origin, disable_gpu=self._disable_gpu,
        )
        self.get_logger().info(f"Lancement du kiosk -> {self._url} (DISPLAY={self._display})")
        self._proc = subprocess.Popen(
            args, env=self._env(),
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )

    def _watchdog(self):
        if self._shutting_down or self._proc is None:
            return
        if self._proc.poll() is not None:
            self.get_logger().warn("chromium s'est arrêté, relance…")
            self._launch()

    def destroy_node(self):
        self._shutting_down = True
        proc = getattr(self, "_proc", None)
        if proc is not None and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = KioskNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
