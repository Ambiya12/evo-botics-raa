#pragma once

#include <algorithm>
#include <cmath>
#include <cstddef>
#include <string>

#include "nav_msgs/msg/occupancy_grid.hpp"
#include "tf2_geometry_msgs/tf2_geometry_msgs.hpp"
#include "tf2/utils.h"

namespace evo_navigation::grid_utils
{

enum class CellStatus
{
  Free,
  Unknown,
  Occupied,
  Outside
};

inline bool worldToMap(
  const nav_msgs::msg::OccupancyGrid & grid,
  const double wx,
  const double wy,
  unsigned int & mx,
  unsigned int & my)
{
  if (grid.info.resolution <= 0.0F || grid.info.width == 0 || grid.info.height == 0) {
    return false;
  }

  const auto & origin = grid.info.origin;
  const auto yaw = tf2::getYaw(origin.orientation);
  const auto dx = wx - origin.position.x;
  const auto dy = wy - origin.position.y;
  const auto cos_yaw = std::cos(yaw);
  const auto sin_yaw = std::sin(yaw);
  const auto local_x = cos_yaw * dx + sin_yaw * dy;
  const auto local_y = -sin_yaw * dx + cos_yaw * dy;

  if (local_x < 0.0 || local_y < 0.0) {
    return false;
  }

  mx = static_cast<unsigned int>(local_x / grid.info.resolution);
  my = static_cast<unsigned int>(local_y / grid.info.resolution);
  return mx < grid.info.width && my < grid.info.height;
}

inline int cellValue(
  const nav_msgs::msg::OccupancyGrid & grid,
  const unsigned int mx,
  const unsigned int my)
{
  const auto index = static_cast<size_t>(my) * grid.info.width + mx;
  if (index >= grid.data.size()) {
    return -1;
  }
  return static_cast<int>(grid.data[index]);
}

inline int occupancyThresholdFromCostmapThreshold(const int path_cost_threshold)
{
  if (path_cost_threshold <= 100) {
    return std::clamp(path_cost_threshold, 1, 100);
  }
  return std::clamp(
    static_cast<int>(std::ceil(static_cast<double>(path_cost_threshold) * 100.0 / 255.0)),
    1, 100);
}

inline CellStatus classifyMapCell(
  const nav_msgs::msg::OccupancyGrid & grid,
  const double wx,
  const double wy,
  const int map_occupied_threshold)
{
  unsigned int mx;
  unsigned int my;
  if (!worldToMap(grid, wx, wy, mx, my)) {
    return CellStatus::Outside;
  }
  const auto value = cellValue(grid, mx, my);
  if (value < 0) {
    return CellStatus::Unknown;
  }
  if (value >= map_occupied_threshold) {
    return CellStatus::Occupied;
  }
  return CellStatus::Free;
}

inline CellStatus classifyCostmapCell(
  const nav_msgs::msg::OccupancyGrid & grid,
  const double wx,
  const double wy,
  const int path_cost_threshold)
{
  unsigned int mx;
  unsigned int my;
  if (!worldToMap(grid, wx, wy, mx, my)) {
    return CellStatus::Outside;
  }
  const auto value = cellValue(grid, mx, my);
  if (value < 0) {
    return CellStatus::Unknown;
  }
  if (value >= occupancyThresholdFromCostmapThreshold(path_cost_threshold)) {
    return CellStatus::Occupied;
  }
  return CellStatus::Free;
}

inline bool hasClearance(
  const nav_msgs::msg::OccupancyGrid & grid,
  const double wx,
  const double wy,
  const double goal_clearance_m,
  const int path_cost_threshold,
  std::string & reason)
{
  unsigned int mx;
  unsigned int my;
  if (!worldToMap(grid, wx, wy, mx, my)) {
    reason = "rejected_outside_map";
    return false;
  }

  const auto radius_cells = static_cast<int>(
    std::ceil(goal_clearance_m / std::max(0.001F, grid.info.resolution)));
  const auto threshold = occupancyThresholdFromCostmapThreshold(path_cost_threshold);

  for (int dy = -radius_cells; dy <= radius_cells; ++dy) {
    for (int dx = -radius_cells; dx <= radius_cells; ++dx) {
      if (std::hypot(dx, dy) > static_cast<double>(radius_cells)) {
        continue;
      }
      const auto x = static_cast<int>(mx) + dx;
      const auto y = static_cast<int>(my) + dy;
      if (x < 0 || y < 0 ||
        x >= static_cast<int>(grid.info.width) ||
        y >= static_cast<int>(grid.info.height))
      {
        reason = "rejected_unknown";
        return false;
      }
      const auto value = cellValue(grid, static_cast<unsigned int>(x), static_cast<unsigned int>(y));
      if (value < 0) {
        reason = "rejected_unknown";
        return false;
      }
      if (value >= threshold) {
        reason = "rejected_occupied";
        return false;
      }
    }
  }

  return true;
}

}  // namespace evo_navigation::grid_utils
