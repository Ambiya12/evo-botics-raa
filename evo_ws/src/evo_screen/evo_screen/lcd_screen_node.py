#!/usr/bin/env python3
"""Node ROS2 : affiche 'Welcome' plein écran sur le LCD HDMI via un service Trigger.

Usage:
  ros2 run evo_screen lcd_screen_node
  ros2 service call /lcd_screen_node/show_welcome std_srvs/srv/Trigger
"""
import rclpy
from rclpy.node import Node
from std_srvs.srv import Trigger

from evo_screen.lcd_renderer import render_welcome, DEFAULT_FONT_PATH
from evo_screen.lcd_adapter import HdmiCvAdapter
from evo_screen.display_state import DisplayState


class LcdScreenNode(Node):
    def __init__(self):
        super().__init__("lcd_screen_node")
        self.declare_parameter("duration", 10.0)
        self.declare_parameter("font_path", DEFAULT_FONT_PATH)
        self.declare_parameter("font_size", 120)
        self.declare_parameter("width", 1024)
        self.declare_parameter("height", 600)

        self._state = DisplayState()
        self._adapter = None  # lazy : créé au 1er affichage, le node démarre même sans écran
        self._srv = self.create_service(Trigger, "~/show_welcome", self._on_show)
        self._timer = self.create_timer(0.03, self._on_tick)
        self.get_logger().info(
            "evo_screen prêt : appeler ~/show_welcome pour afficher Welcome")

    def _now_s(self) -> float:
        return self.get_clock().now().nanoseconds / 1e9

    def _on_show(self, request, response):
        try:
            width = self.get_parameter("width").value
            height = self.get_parameter("height").value
            font_path = self.get_parameter("font_path").value
            font_size = self.get_parameter("font_size").value
            duration = float(self.get_parameter("duration").value)
            image = render_welcome(width, height,
                                   font_path=font_path, font_size=font_size)
            if self._adapter is None:
                self._adapter = HdmiCvAdapter()
            self._adapter.show(image)
            self._state.request(self._now_s(), duration)
            response.success = True
            response.message = f"Affichage Welcome pendant {duration:.0f}s"
        except Exception as exc:  # panne écran/X/cv2 -> échec propre, pas de crash
            self.get_logger().error(f"show_welcome a échoué : {exc}")
            response.success = False
            response.message = str(exc)
        return response

    def _on_tick(self):
        if not self._state.active or self._adapter is None:
            return
        try:
            if self._state.should_clear(self._now_s()):
                self._adapter.clear()
                self._state.mark_cleared()
            else:
                self._adapter.pump()
        except Exception as exc:  # une panne X/cv2 en cours d'affichage ne doit pas crasher le node
            self.get_logger().error(f"tick affichage a échoué : {exc}")
            self._state.mark_cleared()


def main(args=None):
    rclpy.init(args=args)
    node = LcdScreenNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if node._adapter is not None:
            node._adapter.clear()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
