#!/usr/bin/env python3
"""Relay dashboard arm commands through a native volatile ROS publisher."""

import rclpy
from arm_msgs.msg import ArmJoints
from rclpy.node import Node


class ArmCommandRelayNode(Node):
    def __init__(self) -> None:
        super().__init__("arm_command_relay")
        input_topic = self.declare_parameter(
            "input_topic", "/evo/arm/command"
        ).value
        output_topic = self.declare_parameter(
            "output_topic", "/arm6_joints"
        ).value

        self.publisher = self.create_publisher(ArmJoints, output_topic, 10)
        self.subscription = self.create_subscription(
            ArmJoints,
            input_topic,
            self.publisher.publish,
            10,
        )
        self.get_logger().info(
            f"Arm command relay ready: {input_topic} -> {output_topic}"
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
