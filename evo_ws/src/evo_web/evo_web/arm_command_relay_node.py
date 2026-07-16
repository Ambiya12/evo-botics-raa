#!/usr/bin/env python3
"""Relay dashboard arm commands through a native volatile ROS publisher."""

import rclpy
from arm_msgs.msg import ArmJoints
from rclpy.node import Node

JOINT_LIMITS = {
    "joint1": (0, 180),
    "joint2": (0, 180),
    "joint3": (0, 180),
    "joint4": (0, 180),
    "joint5": (0, 180),
    "joint6": (20, 150),
}


class ArmCommandRelayNode(Node):
    def __init__(self) -> None:
        super().__init__("arm_command_relay")
        input_topic = self.declare_parameter(
            "input_topic", "/evo/arm/command"
        ).value
        output_topic = self.declare_parameter(
            "output_topic", "/arm6_joints"
        ).value
        self.min_time_ms = int(self.declare_parameter("min_time_ms", 100).value)
        self.max_time_ms = int(self.declare_parameter("max_time_ms", 3000).value)

        self.publisher = self.create_publisher(ArmJoints, output_topic, 10)
        self.subscription = self.create_subscription(
            ArmJoints,
            input_topic,
            self.relay_command,
            10,
        )
        self.output_topic = str(output_topic)
        self.get_logger().info(
            f"Arm command relay ready: {input_topic} -> {output_topic}"
        )

    def relay_command(self, msg: ArmJoints) -> None:
        command = ArmJoints()
        for field, (minimum, maximum) in JOINT_LIMITS.items():
            try:
                value = int(round(float(getattr(msg, field))))
            except (TypeError, ValueError, OverflowError):
                self.get_logger().error(f"Dropped invalid arm command field: {field}")
                return
            setattr(command, field, max(minimum, min(maximum, value)))
        try:
            time_ms = int(round(float(msg.time)))
        except (TypeError, ValueError, OverflowError):
            self.get_logger().error("Dropped invalid arm command field: time")
            return
        command.time = max(self.min_time_ms, min(self.max_time_ms, time_ms))

        subscriber_count = self.publisher.get_subscription_count()
        if subscriber_count < 1:
            self.get_logger().warning(
                f"Relaying arm command to {self.output_topic}, but no subscribers are visible"
            )

        self.publisher.publish(command)
        self.get_logger().info(
            "Relayed arm command "
            f"[{command.joint1}, {command.joint2}, {command.joint3}, "
            f"{command.joint4}, {command.joint5}, {command.joint6}] "
            f"time={command.time}ms subscribers={subscriber_count}"
        )


def main(args=None) -> None:
    rclpy.init(args=args)
    node = ArmCommandRelayNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
