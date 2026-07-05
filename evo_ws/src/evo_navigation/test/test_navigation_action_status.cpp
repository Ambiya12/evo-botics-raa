#include <gtest/gtest.h>

#include "evo_navigation/navigation_action_status.hpp"

TEST(NavigationActionStatus, RejectsDispatchWhenServerIsUnavailable)
{
  EXPECT_EQ(
    evo_navigation::navigationDispatchDecision(false, false),
    evo_navigation::NavigationDispatchDecision::SERVER_UNAVAILABLE);
  EXPECT_EQ(
    evo_navigation::navigationDispatchDecision(false, true),
    evo_navigation::NavigationDispatchDecision::SERVER_UNAVAILABLE);
}

TEST(NavigationActionStatus, SendsDirectlyWithoutAnActiveGoal)
{
  EXPECT_EQ(
    evo_navigation::navigationDispatchDecision(true, false),
    evo_navigation::NavigationDispatchDecision::SEND);
}

TEST(NavigationActionStatus, ReplacesAnActiveGoal)
{
  EXPECT_EQ(
    evo_navigation::navigationDispatchDecision(true, true),
    evo_navigation::NavigationDispatchDecision::CANCEL_THEN_SEND);
}

TEST(NavigationActionStatus, MapsSuccessfulResult)
{
  EXPECT_EQ(
    evo_navigation::navigationStatusFromResult(rclcpp_action::ResultCode::SUCCEEDED),
    "succeeded");
}

TEST(NavigationActionStatus, MapsCancelledResult)
{
  EXPECT_EQ(
    evo_navigation::navigationStatusFromResult(rclcpp_action::ResultCode::CANCELED),
    "cancelled");
}

TEST(NavigationActionStatus, MapsAbortedAndUnknownResultsToFailure)
{
  EXPECT_EQ(
    evo_navigation::navigationStatusFromResult(rclcpp_action::ResultCode::ABORTED),
    "failed");
  EXPECT_EQ(
    evo_navigation::navigationStatusFromResult(rclcpp_action::ResultCode::UNKNOWN),
    "failed");
}
