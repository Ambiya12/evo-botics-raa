#include <chrono>
#include <algorithm>
#include <memory>
#include <string>

#include "geometry_msgs/msg/twist.hpp"
#include "rclcpp/rclcpp.hpp"
#include "std_msgs/msg/bool.hpp"

using namespace std::chrono_literals;

namespace evo_navigation
{

class CmdVelSafetyGate : public rclcpp::Node
{
public:
  CmdVelSafetyGate() : Node("cmd_vel_safety_gate")
  {
    const auto nav_topic = declare_parameter<std::string>("nav_cmd_topic", "/cmd_vel_nav");
    const auto teleop_topic = declare_parameter<std::string>("teleop_cmd_topic", "/cmd_vel_teleop");
    const auto output_topic = declare_parameter<std::string>("output_cmd_topic", "/cmd_vel");
    const auto estop_topic = declare_parameter<std::string>("estop_topic", "/e_stop");
    const auto reset_topic = declare_parameter<std::string>("reset_topic", "/e_stop_reset");
    const auto status_topic = declare_parameter<std::string>("status_topic", "/e_stop_active");
    const auto zero_hz = declare_parameter<double>("zero_publish_hz", 20.0);
    input_timeout_s_ = declare_parameter<double>("input_timeout_s", 0.5);
    teleop_priority_timeout_s_ =
      declare_parameter<double>("teleop_priority_timeout_s", 0.3);

    cmd_pub_ = create_publisher<geometry_msgs::msg::Twist>(output_topic, 10);

    rclcpp::QoS status_qos(1);
    status_qos.transient_local().reliable();
    estop_status_pub_ = create_publisher<std_msgs::msg::Bool>(status_topic, status_qos);

    nav_sub_ = create_subscription<geometry_msgs::msg::Twist>(
        nav_topic, 10,
        [this](const geometry_msgs::msg::Twist::SharedPtr msg) {
          if (teleopHasPriority()) {
            return;
          }
          last_input_time_ = now();
          forwardIfSafe(*msg);
        });

    teleop_sub_ = create_subscription<geometry_msgs::msg::Twist>(
        teleop_topic, 10,
        [this](const geometry_msgs::msg::Twist::SharedPtr msg) {
          last_teleop_time_ = now();
          last_input_time_ = last_teleop_time_;
          forwardIfSafe(*msg);
        });

    estop_sub_ = create_subscription<std_msgs::msg::Bool>(
        estop_topic, 10,
        [this](const std_msgs::msg::Bool::SharedPtr msg) {
          if (msg->data) {
            latchEstop();
          }
        });

    reset_sub_ = create_subscription<std_msgs::msg::Bool>(
        reset_topic, 10,
        [this](const std_msgs::msg::Bool::SharedPtr msg) {
          if (msg->data) {
            resetEstop();
          }
        });

    const auto period = std::chrono::duration<double>(1.0 / std::max(1.0, zero_hz));
    zero_timer_ = create_wall_timer(
        std::chrono::duration_cast<std::chrono::milliseconds>(period),
        [this]() {
          if (estop_active_) {
            publishZero();
            return;
          }
          if (last_input_time_.nanoseconds() != 0 &&
              (now() - last_input_time_).seconds() > input_timeout_s_) {
            publishZero();
          }
        });

    publishEstopStatus();
    RCLCPP_INFO(
        get_logger(),
        "cmd_vel safety gate ready: nav=%s teleop=%s output=%s estop=%s reset=%s "
        "teleop_priority_timeout=%.2fs input_timeout=%.2fs",
        nav_topic.c_str(), teleop_topic.c_str(), output_topic.c_str(),
        estop_topic.c_str(), reset_topic.c_str(), teleop_priority_timeout_s_,
        input_timeout_s_);
  }

private:
  bool teleopHasPriority() const
  {
    return last_teleop_time_.nanoseconds() != 0 &&
           (now() - last_teleop_time_).seconds() <= teleop_priority_timeout_s_;
  }

  void forwardIfSafe(const geometry_msgs::msg::Twist & msg)
  {
    if (estop_active_) {
      publishZero();
      return;
    }
    cmd_pub_->publish(msg);
  }

  void latchEstop()
  {
    if (!estop_active_) {
      RCLCPP_ERROR(get_logger(), "Emergency stop latched. Publishing zero velocity until reset.");
      estop_active_ = true;
      publishEstopStatus();
    }
    publishZero();
  }

  void resetEstop()
  {
    if (!estop_active_) {
      publishEstopStatus();
      return;
    }
    estop_active_ = false;
    publishZero();
    publishEstopStatus();
    RCLCPP_WARN(get_logger(), "Emergency stop reset. Motion commands are allowed again.");
  }

  void publishZero()
  {
    cmd_pub_->publish(geometry_msgs::msg::Twist());
  }

  void publishEstopStatus()
  {
    std_msgs::msg::Bool msg;
    msg.data = estop_active_;
    estop_status_pub_->publish(msg);
  }

  bool estop_active_{false};
  double input_timeout_s_{0.5};
  double teleop_priority_timeout_s_{0.3};
  rclcpp::Time last_input_time_{0, 0, RCL_ROS_TIME};
  rclcpp::Time last_teleop_time_{0, 0, RCL_ROS_TIME};
  rclcpp::Publisher<geometry_msgs::msg::Twist>::SharedPtr cmd_pub_;
  rclcpp::Publisher<std_msgs::msg::Bool>::SharedPtr estop_status_pub_;
  rclcpp::Subscription<geometry_msgs::msg::Twist>::SharedPtr nav_sub_;
  rclcpp::Subscription<geometry_msgs::msg::Twist>::SharedPtr teleop_sub_;
  rclcpp::Subscription<std_msgs::msg::Bool>::SharedPtr estop_sub_;
  rclcpp::Subscription<std_msgs::msg::Bool>::SharedPtr reset_sub_;
  rclcpp::TimerBase::SharedPtr zero_timer_;
};

}  // namespace evo_navigation

int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<evo_navigation::CmdVelSafetyGate>());
  rclcpp::shutdown();
  return 0;
}
