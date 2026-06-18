#!/usr/bin/env python3
"""Node ROS2 : miroir du topic /reception/qr/status sur le LCD HDMI.

Usage:
  ros2 run evo_screen lcd_screen_node
  ros2 topic pub --once /reception/qr/status std_msgs/msg/String "{data: '{\"state\":\"success\"}'}"
"""
import rclpy
from rclpy.node import Node
from std_msgs.msg import String

from evo_screen.lcd_adapter import HdmiCvAdapter
from evo_screen.lcd_renderer import DEFAULT_FONT_PATH
from evo_screen.screen_controller import ScreenController

STATUS_TOPIC = "/reception/qr/status"


class LcdScreenNode(Node):
    def __init__(self):
        super().__init__("lcd_screen_node")
        self.declare_parameter("duration", 10.0)
        self.declare_parameter("font_path", DEFAULT_FONT_PATH)
        self.declare_parameter("font_size", 96)
        self.declare_parameter("width", 1024)
        self.declare_parameter("height", 600)

        adapter = None
        try:
            adapter = HdmiCvAdapter()  # importe cv2 ; peut échouer sans écran/X
        except Exception as exc:
            self.get_logger().error(f"adapter HDMI indisponible : {exc}")

        self._controller = ScreenController(
            adapter,
            width=self.get_parameter("width").value,
            height=self.get_parameter("height").value,
            font_path=self.get_parameter("font_path").value,
            font_size=self.get_parameter("font_size").value,
            duration=float(self.get_parameter("duration").value),
        )

        try:
            self._controller.show_welcome()  # boot : welcome dès le démarrage
        except Exception as exc:
            self.get_logger().error(f"affichage welcome au boot a échoué : {exc}")

        self.create_subscription(String, STATUS_TOPIC, self._on_status, 10)
        self.create_timer(0.03, self._on_tick)
        self.get_logger().info(f"evo_screen prêt : abonné à {STATUS_TOPIC}")

    def _now_s(self) -> float:
        return self.get_clock().now().nanoseconds / 1e9

    def _on_status(self, msg: String):
        try:
            if not self._controller.on_status(msg.data, self._now_s()):
                self.get_logger().warning(f"message /reception/qr/status ignoré : {msg.data!r}")
        except Exception as exc:  # panne X/cv2 -> pas de crash
            self.get_logger().error(f"traitement du statut a échoué : {exc}")
            self._controller.abort()

    def _on_tick(self):
        try:
            self._controller.tick(self._now_s())
        except Exception as exc:  # panne X/cv2 en cours d'affichage -> pas de crash
            self.get_logger().error(f"tick affichage a échoué : {exc}")
            self._controller.abort()


def main(args=None):
    rclpy.init(args=args)
    node = LcdScreenNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node._controller.shutdown()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
