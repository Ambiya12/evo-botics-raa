#pragma once

#include <string>

#include "rclcpp_action/rclcpp_action.hpp"

namespace evo_navigation
{

enum class NavigationDispatchDecision
{
  SERVER_UNAVAILABLE,
  SEND,
  CANCEL_THEN_SEND,
};

inline NavigationDispatchDecision navigationDispatchDecision(
  const bool server_available,
  const bool has_active_goal)
{
  if (!server_available) {
    return NavigationDispatchDecision::SERVER_UNAVAILABLE;
  }
  return has_active_goal ?
         NavigationDispatchDecision::CANCEL_THEN_SEND :
         NavigationDispatchDecision::SEND;
}

inline std::string navigationStatusFromResult(const rclcpp_action::ResultCode code)
{
  switch (code) {
    case rclcpp_action::ResultCode::SUCCEEDED:
      return "succeeded";
    case rclcpp_action::ResultCode::CANCELED:
      return "cancelled";
    default:
      return "failed";
  }
}

}  // namespace evo_navigation
