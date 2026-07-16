#include <chrono>
#include <memory>
#include <string>

#include "geometry_msgs/msg/twist.hpp"
#include "rclcpp/rclcpp.hpp"

using namespace std::chrono_literals;

namespace evo_navigation
{

class CmdVelOutputRelay : public rclcpp::Node
{
public:
  CmdVelOutputRelay() : Node("cmd_vel_output_relay")
  {
    const auto input_topic = declare_parameter<std::string>("input_cmd_topic", "/cmd_vel_safe");
    const auto fallback_topic = declare_parameter<std::string>("fallback_cmd_topic", "");
    const auto output_topic = declare_parameter<std::string>("output_cmd_topic", "/cmd_vel");
    timeout_s_ = declare_parameter<double>("input_timeout_s", 0.5);

    cmd_pub_ = create_publisher<geometry_msgs::msg::Twist>(output_topic, 10);
    cmd_sub_ = create_subscription<geometry_msgs::msg::Twist>(
      input_topic, 10,
      [this](const geometry_msgs::msg::Twist::SharedPtr msg) {
        last_input_time_ = now();
        cmd_pub_->publish(*msg);
      });

    if (!fallback_topic.empty()) {
      fallback_sub_ = create_subscription<geometry_msgs::msg::Twist>(
        fallback_topic, 10,
        [this](const geometry_msgs::msg::Twist::SharedPtr msg) {
          if (last_input_time_.nanoseconds() == 0) {
            cmd_pub_->publish(*msg);
          }
        });
    }

    watchdog_timer_ = create_wall_timer(100ms, [this]() {
      if (last_input_time_.nanoseconds() == 0) {
        return;
      }

      if ((now() - last_input_time_).seconds() > timeout_s_) {
        cmd_pub_->publish(geometry_msgs::msg::Twist());
      }
    });

    RCLCPP_INFO(
      get_logger(), "cmd_vel output relay ready: input=%s fallback=%s output=%s timeout=%.2fs",
      input_topic.c_str(), fallback_topic.empty() ? "<disabled>" : fallback_topic.c_str(),
      output_topic.c_str(), timeout_s_);
  }

private:
  double timeout_s_{0.5};
  rclcpp::Time last_input_time_{0, 0, RCL_ROS_TIME};
  rclcpp::Publisher<geometry_msgs::msg::Twist>::SharedPtr cmd_pub_;
  rclcpp::Subscription<geometry_msgs::msg::Twist>::SharedPtr cmd_sub_;
  rclcpp::Subscription<geometry_msgs::msg::Twist>::SharedPtr fallback_sub_;
  rclcpp::TimerBase::SharedPtr watchdog_timer_;
};

}  // namespace evo_navigation

int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<evo_navigation::CmdVelOutputRelay>());
  rclcpp::shutdown();
  return 0;
}
