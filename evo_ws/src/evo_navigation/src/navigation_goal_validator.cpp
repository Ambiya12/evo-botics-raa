#include <algorithm>
#include <chrono>
#include <cmath>
#include <memory>
#include <mutex>
#include <string>

#include "geometry_msgs/msg/pose_stamped.hpp"
#include "evo_navigation/navigation_action_status.hpp"
#include "evo_navigation/occupancy_grid_utils.hpp"
#include "nav2_msgs/action/compute_path_to_pose.hpp"
#include "nav2_msgs/action/navigate_to_pose.hpp"
#include "nav_msgs/msg/occupancy_grid.hpp"
#include "nav_msgs/msg/path.hpp"
#include "rclcpp/rclcpp.hpp"
#include "rclcpp_action/rclcpp_action.hpp"
#include "std_msgs/msg/bool.hpp"
#include "std_msgs/msg/string.hpp"
#include "tf2/utils.h"
#include "tf2_geometry_msgs/tf2_geometry_msgs.hpp"
#include "tf2_ros/buffer.h"
#include "tf2_ros/transform_listener.h"

using namespace std::chrono_literals;

namespace evo_navigation
{

class NavigationGoalValidator : public rclcpp::Node
{
public:
  using ComputePathToPose = nav2_msgs::action::ComputePathToPose;
  using GoalHandleComputePath = rclcpp_action::ClientGoalHandle<ComputePathToPose>;
  using NavigateToPose = nav2_msgs::action::NavigateToPose;
  using GoalHandleNavigateToPose = rclcpp_action::ClientGoalHandle<NavigateToPose>;

  NavigationGoalValidator()
  : Node("navigation_goal_validator"),
    tf_buffer_(get_clock()),
    tf_listener_(tf_buffer_)
  {
    target_frame_ = declare_parameter<std::string>("target_frame", "map");
    navigation_mode_ = declare_parameter<std::string>("navigation_mode", "mapped_free_space");
    enforce_mapped_space_ = declare_parameter<bool>("enforce_mapped_space", true);
    goal_clearance_m_ = declare_parameter<double>("goal_clearance_m", 0.25);
    transform_timeout_s_ = declare_parameter<double>("transform_timeout_s", 0.5);
    path_sample_step_m_ = declare_parameter<double>("path_sample_step_m", 0.05);
    planner_id_ = declare_parameter<std::string>("planner_id", "GridBased");
    map_occupied_threshold_ = declare_parameter<int>("map_occupied_threshold", 65);
    path_cost_threshold_ = declare_parameter<int>("path_cost_threshold", 95);
    planner_action_name_ =
      declare_parameter<std::string>("planner_action_name", "/compute_path_to_pose");
    nav2_action_name_ =
      declare_parameter<std::string>("nav2_action_name", "/navigate_to_pose");

    const auto goal_request_topic =
      declare_parameter<std::string>("goal_request_topic", "/evo/navigation/goal_request");
    const auto validated_goal_topic =
      declare_parameter<std::string>("validated_goal_topic", "/goal_pose_validated");
    const auto status_topic =
      declare_parameter<std::string>("status_topic", "/evo/navigation/goal_status");
    const auto estop_status_topic =
      declare_parameter<std::string>("estop_status_topic", "/e_stop_active");
    const auto map_topic = declare_parameter<std::string>("map_topic", "/map");
    const auto costmap_topic =
      declare_parameter<std::string>("costmap_topic", "/global_costmap/costmap");

    rclcpp::QoS map_qos(1);
    map_qos.transient_local().reliable();
    map_sub_ = create_subscription<nav_msgs::msg::OccupancyGrid>(
      map_topic, map_qos,
      [this](const nav_msgs::msg::OccupancyGrid::SharedPtr msg) {
        std::lock_guard<std::mutex> lock(data_mutex_);
        map_ = msg;
      });

    rclcpp::QoS costmap_qos(1);
    costmap_qos.reliable();
    costmap_sub_ = create_subscription<nav_msgs::msg::OccupancyGrid>(
      costmap_topic, costmap_qos,
      [this](const nav_msgs::msg::OccupancyGrid::SharedPtr msg) {
        std::lock_guard<std::mutex> lock(data_mutex_);
        costmap_ = msg;
      });

    validated_goal_pub_ = create_publisher<geometry_msgs::msg::PoseStamped>(validated_goal_topic, 10);
    status_pub_ = create_publisher<std_msgs::msg::String>(status_topic, 10);
    rclcpp::QoS estop_qos(1);
    estop_qos.transient_local().reliable();
    estop_sub_ = create_subscription<std_msgs::msg::Bool>(
      estop_status_topic, estop_qos,
      [this](const std_msgs::msg::Bool::SharedPtr msg) {
        estop_state_received_ = true;
        estop_active_ = msg->data;
        if (!estop_active_) {
          return;
        }

        const auto invalidated_request_id = ++latest_request_id_;
        active_request_id_ = invalidated_request_id;
        if (active_navigation_goal_) {
          navigation_client_->async_cancel_goal(active_navigation_goal_);
          active_navigation_goal_.reset();
        }
        publishStatus("emergency_stopped");
      });
    planner_client_ = rclcpp_action::create_client<ComputePathToPose>(this, planner_action_name_);
    navigation_client_ =
      rclcpp_action::create_client<NavigateToPose>(this, nav2_action_name_);

    goal_sub_ = create_subscription<geometry_msgs::msg::PoseStamped>(
      goal_request_topic, 10,
      [this](const geometry_msgs::msg::PoseStamped::SharedPtr msg) {
        handleGoalRequest(*msg);
      });

    if (navigation_mode_ == "road_network_only") {
      RCLCPP_WARN(
        get_logger(),
        "navigation_mode=road_network_only is reserved for a future route-graph implementation; "
        "incoming goals will be rejected.");
    } else if (navigation_mode_ != "mapped_free_space" && navigation_mode_ != "exploration") {
      RCLCPP_WARN(
        get_logger(),
        "Unsupported navigation_mode=%s; incoming goals will be rejected.",
        navigation_mode_.c_str());
    }

    RCLCPP_INFO(
      get_logger(),
      "navigation goal validator ready: mode=%s request=%s validated=%s status=%s "
      "planner=%s navigator=%s frame=%s map=%s costmap=%s estop=%s",
      navigation_mode_.c_str(),
      goal_request_topic.c_str(), validated_goal_topic.c_str(), status_topic.c_str(),
      planner_action_name_.c_str(), nav2_action_name_.c_str(), target_frame_.c_str(),
      map_topic.c_str(), costmap_topic.c_str(), estop_status_topic.c_str());
  }

private:
  void handleGoalRequest(const geometry_msgs::msg::PoseStamped & request)
  {
    const auto request_id = ++latest_request_id_;
    RCLCPP_INFO(
      get_logger(), "Received navigation goal request %lu: frame=%s x=%.3f y=%.3f",
      request_id, request.header.frame_id.c_str(),
      request.pose.position.x, request.pose.position.y);

    if (!estop_state_received_) {
      publishStatus("rejected_estop_state_unavailable");
      return;
    }
    if (estop_active_) {
      publishStatus("rejected_estop_active");
      return;
    }

    if (navigation_mode_ == "road_network_only" ||
      (navigation_mode_ != "mapped_free_space" && navigation_mode_ != "exploration"))
    {
      publishStatus("rejected_unsupported_mode");
      return;
    }

    geometry_msgs::msg::PoseStamped goal;
    if (!transformGoal(request, goal)) {
      publishStatus("rejected_frame_transform");
      return;
    }
    RCLCPP_INFO(
      get_logger(), "Goal request %lu transformed: frame=%s x=%.3f y=%.3f",
      request_id, goal.header.frame_id.c_str(), goal.pose.position.x, goal.pose.position.y);

    std::string reason;
    if (!validateGoalCell(goal, reason)) {
      RCLCPP_WARN(get_logger(), "Goal request %lu rejected: %s", request_id, reason.c_str());
      publishStatus(reason);
      return;
    }
    RCLCPP_INFO(get_logger(), "Goal request %lu passed map and clearance validation", request_id);

    if (!planner_client_->wait_for_action_server(1s)) {
      RCLCPP_WARN(get_logger(), "Planner action server %s is not available", planner_action_name_.c_str());
      publishStatus("rejected_no_path");
      return;
    }

    ComputePathToPose::Goal planner_goal;
    planner_goal.goal = goal;
    planner_goal.planner_id = planner_id_;
    planner_goal.use_start = false;

    auto send_goal_options = rclcpp_action::Client<ComputePathToPose>::SendGoalOptions();
    send_goal_options.goal_response_callback =
      [this, request_id](const GoalHandleComputePath::SharedPtr & handle) {
        if (request_id != latest_request_id_) {
          return;
        }
        if (!handle) {
          RCLCPP_WARN(get_logger(), "Planner rejected goal request %lu", request_id);
          publishStatus("rejected_no_path");
        }
      };
    send_goal_options.result_callback =
      [this, goal, request_id](const GoalHandleComputePath::WrappedResult & result) {
        if (request_id != latest_request_id_) {
          RCLCPP_INFO(get_logger(), "Ignoring stale planner result for goal request %lu", request_id);
          return;
        }
        if (result.code != rclcpp_action::ResultCode::SUCCEEDED || !result.result) {
          RCLCPP_WARN(
            get_logger(), "Planner failed goal request %lu with result code %d",
            request_id, static_cast<int>(result.code));
          publishStatus("rejected_no_path");
          return;
        }

        std::string reason;
        if (!validatePath(result.result->path, reason)) {
          RCLCPP_WARN(get_logger(), "Planned path for request %lu rejected: %s", request_id, reason.c_str());
          publishStatus(reason);
          return;
        }

        RCLCPP_INFO(
          get_logger(), "Goal request %lu validated with %zu path poses",
          request_id, result.result->path.poses.size());
        validated_goal_pub_->publish(goal);
        publishStatus("accepted");
        replaceNavigationGoal(goal, request_id);
      };

    planner_client_->async_send_goal(planner_goal, send_goal_options);
    publishStatus("planning");
  }

  void replaceNavigationGoal(
    const geometry_msgs::msg::PoseStamped & goal,
    const uint64_t request_id)
  {
    const auto dispatch_decision = navigationDispatchDecision(
      navigation_client_->wait_for_action_server(1s),
      static_cast<bool>(active_navigation_goal_));
    if (dispatch_decision == NavigationDispatchDecision::SERVER_UNAVAILABLE) {
      RCLCPP_ERROR(
        get_logger(), "Nav2 action server %s is not available for goal request %lu",
        nav2_action_name_.c_str(), request_id);
      publishStatus("failed");
      return;
    }

    active_request_id_ = request_id;
    if (dispatch_decision == NavigationDispatchDecision::SEND) {
      sendNavigationGoal(goal, request_id);
      return;
    }

    RCLCPP_INFO(
      get_logger(), "Cancelling active Nav2 goal before dispatching request %lu", request_id);
    navigation_client_->async_cancel_goal(
      active_navigation_goal_,
      [this, goal, request_id](auto) {
        if (request_id != active_request_id_) {
          return;
        }
        active_navigation_goal_.reset();
        publishStatus("cancelled");
        sendNavigationGoal(goal, request_id);
      });
  }

  void sendNavigationGoal(
    const geometry_msgs::msg::PoseStamped & goal,
    const uint64_t request_id)
  {
    NavigateToPose::Goal navigation_goal;
    navigation_goal.pose = goal;

    auto options = rclcpp_action::Client<NavigateToPose>::SendGoalOptions();
    options.goal_response_callback =
      [this, request_id](const GoalHandleNavigateToPose::SharedPtr & handle) {
        if (request_id != active_request_id_) {
          if (handle) {
            navigation_client_->async_cancel_goal(handle);
          }
          return;
        }
        if (!handle) {
          RCLCPP_ERROR(get_logger(), "Nav2 rejected goal request %lu", request_id);
          publishStatus("failed");
          return;
        }
        active_navigation_goal_ = handle;
        RCLCPP_INFO(get_logger(), "Nav2 accepted goal request %lu", request_id);
        publishStatus("active");
      };
    options.result_callback =
      [this, request_id](const GoalHandleNavigateToPose::WrappedResult & result) {
        if (request_id != active_request_id_) {
          return;
        }
        active_navigation_goal_.reset();
        RCLCPP_INFO(
          get_logger(), "Nav2 completed goal request %lu with result code %d",
          request_id, static_cast<int>(result.code));
        publishStatus(navigationStatusFromResult(result.code));
      };

    RCLCPP_INFO(
      get_logger(), "Sending goal request %lu to Nav2 action %s: x=%.3f y=%.3f frame=%s",
      request_id, nav2_action_name_.c_str(), goal.pose.position.x, goal.pose.position.y,
      goal.header.frame_id.c_str());
    navigation_client_->async_send_goal(navigation_goal, options);
  }

  bool transformGoal(
    const geometry_msgs::msg::PoseStamped & input,
    geometry_msgs::msg::PoseStamped & output)
  {
    if (input.header.frame_id.empty() || input.header.frame_id == target_frame_) {
      output = input;
      output.header.frame_id = target_frame_;
      output.header.stamp = now();
      return true;
    }

    try {
      output = tf_buffer_.transform(
        input, target_frame_, tf2::durationFromSec(transform_timeout_s_));
      output.header.stamp = now();
      return true;
    } catch (const tf2::TransformException & ex) {
      RCLCPP_WARN(
        get_logger(), "Could not transform goal from %s to %s: %s",
        input.header.frame_id.c_str(), target_frame_.c_str(), ex.what());
      return false;
    }
  }

  bool validateGoalCell(
    const geometry_msgs::msg::PoseStamped & goal,
    std::string & reason)
  {
    if (!enforce_mapped_space_) {
      return true;
    }

    nav_msgs::msg::OccupancyGrid::SharedPtr map;
    nav_msgs::msg::OccupancyGrid::SharedPtr costmap;
    {
      std::lock_guard<std::mutex> lock(data_mutex_);
      map = map_;
      costmap = costmap_;
    }

    if (!map) {
      reason = "rejected_map_unavailable";
      return false;
    }

    const auto map_status = classifyMapCell(*map, goal.pose.position.x, goal.pose.position.y);
    if (map_status == CellStatus::Outside) {
      reason = "rejected_outside_map";
      return false;
    }
    if (map_status == CellStatus::Unknown) {
      reason = "rejected_unknown";
      return false;
    }
    if (map_status == CellStatus::Occupied) {
      reason = "rejected_occupied";
      return false;
    }

    if (!costmap) {
      reason = "rejected_costmap_unavailable";
      return false;
    }

    if (!hasClearance(*costmap, goal.pose.position.x, goal.pose.position.y, reason)) {
      return false;
    }

    return true;
  }

  bool validatePath(const nav_msgs::msg::Path & path, std::string & reason)
  {
    if (!enforce_mapped_space_) {
      return true;
    }
    if (path.poses.empty()) {
      reason = "rejected_no_path";
      return false;
    }

    nav_msgs::msg::OccupancyGrid::SharedPtr map;
    nav_msgs::msg::OccupancyGrid::SharedPtr costmap;
    {
      std::lock_guard<std::mutex> lock(data_mutex_);
      map = map_;
      costmap = costmap_;
    }

    if (!map || !costmap) {
      reason = "rejected_costmap_unavailable";
      return false;
    }

    for (size_t i = 0; i < path.poses.size(); ++i) {
      if (!validatePathPoint(*map, *costmap, path.poses[i].pose.position.x,
          path.poses[i].pose.position.y, reason))
      {
        return false;
      }

      if (i == 0) {
        continue;
      }

      const auto & previous = path.poses[i - 1].pose.position;
      const auto & current = path.poses[i].pose.position;
      const auto dx = current.x - previous.x;
      const auto dy = current.y - previous.y;
      const auto distance = std::hypot(dx, dy);
      const auto steps = static_cast<int>(
        std::ceil(distance / std::max(0.01, path_sample_step_m_)));

      for (int step = 1; step < steps; ++step) {
        const auto ratio = static_cast<double>(step) / static_cast<double>(steps);
        const auto x = previous.x + dx * ratio;
        const auto y = previous.y + dy * ratio;
        if (!validatePathPoint(*map, *costmap, x, y, reason)) {
          return false;
        }
      }
    }

    return true;
  }

  bool validatePathPoint(
    const nav_msgs::msg::OccupancyGrid & map,
    const nav_msgs::msg::OccupancyGrid & costmap,
    const double x,
    const double y,
    std::string & reason) const
  {
    const auto map_status = classifyMapCell(map, x, y);
    if (map_status == CellStatus::Outside || map_status == CellStatus::Unknown) {
      reason = "rejected_path_unknown";
      return false;
    }
    if (map_status == CellStatus::Occupied) {
      reason = "rejected_path_obstacle";
      return false;
    }

    const auto cost_status = classifyCostmapCell(costmap, x, y);
    if (cost_status == CellStatus::Outside || cost_status == CellStatus::Unknown) {
      reason = "rejected_path_unknown";
      return false;
    }
    if (cost_status == CellStatus::Occupied) {
      reason = "rejected_path_obstacle";
      return false;
    }

    return true;
  }

  using CellStatus = grid_utils::CellStatus;

  CellStatus classifyMapCell(
    const nav_msgs::msg::OccupancyGrid & grid, const double wx, const double wy) const
  {
    return grid_utils::classifyMapCell(grid, wx, wy, map_occupied_threshold_);
  }

  CellStatus classifyCostmapCell(
    const nav_msgs::msg::OccupancyGrid & grid, const double wx, const double wy) const
  {
    return grid_utils::classifyCostmapCell(grid, wx, wy, path_cost_threshold_);
  }

  bool hasClearance(
    const nav_msgs::msg::OccupancyGrid & grid,
    const double wx,
    const double wy,
    std::string & reason) const
  {
    return grid_utils::hasClearance(
      grid, wx, wy, goal_clearance_m_, path_cost_threshold_, reason);
  }

  bool worldToMap(
    const nav_msgs::msg::OccupancyGrid & grid,
    const double wx,
    const double wy,
    unsigned int & mx,
    unsigned int & my) const
  {
    return grid_utils::worldToMap(grid, wx, wy, mx, my);
  }

  int cellValue(
    const nav_msgs::msg::OccupancyGrid & grid,
    const unsigned int mx,
    const unsigned int my) const
  {
    return grid_utils::cellValue(grid, mx, my);
  }

  int occupancyThresholdFromCostmapThreshold() const
  {
    return grid_utils::occupancyThresholdFromCostmapThreshold(path_cost_threshold_);
  }

  void publishStatus(const std::string & code)
  {
    std_msgs::msg::String msg;
    msg.data = code;
    status_pub_->publish(msg);
    if (code != "planning") {
      RCLCPP_INFO(get_logger(), "Navigation goal status: %s", code.c_str());
    }
  }

  std::string target_frame_;
  std::string navigation_mode_;
  std::string planner_id_;
  std::string planner_action_name_;
  std::string nav2_action_name_;
  bool enforce_mapped_space_{true};
  double goal_clearance_m_{0.25};
  double transform_timeout_s_{0.5};
  double path_sample_step_m_{0.05};
  int map_occupied_threshold_{65};
  int path_cost_threshold_{95};
  bool estop_state_received_{false};
  bool estop_active_{false};

  std::mutex data_mutex_;
  nav_msgs::msg::OccupancyGrid::SharedPtr map_;
  nav_msgs::msg::OccupancyGrid::SharedPtr costmap_;

  tf2_ros::Buffer tf_buffer_;
  tf2_ros::TransformListener tf_listener_;
  rclcpp_action::Client<ComputePathToPose>::SharedPtr planner_client_;
  rclcpp_action::Client<NavigateToPose>::SharedPtr navigation_client_;
  GoalHandleNavigateToPose::SharedPtr active_navigation_goal_;
  uint64_t latest_request_id_{0};
  uint64_t active_request_id_{0};
  rclcpp::Subscription<geometry_msgs::msg::PoseStamped>::SharedPtr goal_sub_;
  rclcpp::Subscription<std_msgs::msg::Bool>::SharedPtr estop_sub_;
  rclcpp::Subscription<nav_msgs::msg::OccupancyGrid>::SharedPtr map_sub_;
  rclcpp::Subscription<nav_msgs::msg::OccupancyGrid>::SharedPtr costmap_sub_;
  rclcpp::Publisher<geometry_msgs::msg::PoseStamped>::SharedPtr validated_goal_pub_;
  rclcpp::Publisher<std_msgs::msg::String>::SharedPtr status_pub_;
};

}  // namespace evo_navigation

int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<evo_navigation::NavigationGoalValidator>());
  rclcpp::shutdown();
  return 0;
}
