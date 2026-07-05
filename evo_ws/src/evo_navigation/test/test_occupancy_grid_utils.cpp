#include <string>
#include <vector>

#include "evo_navigation/occupancy_grid_utils.hpp"
#include "gtest/gtest.h"

namespace
{

nav_msgs::msg::OccupancyGrid makeGrid(
  const unsigned int width = 10,
  const unsigned int height = 10,
  const float resolution = 0.1F)
{
  nav_msgs::msg::OccupancyGrid grid;
  grid.info.width = width;
  grid.info.height = height;
  grid.info.resolution = resolution;
  grid.info.origin.orientation.w = 1.0;
  grid.data.assign(width * height, 0);
  return grid;
}

size_t indexOf(
  const nav_msgs::msg::OccupancyGrid & grid,
  const unsigned int x,
  const unsigned int y)
{
  return static_cast<size_t>(y) * grid.info.width + x;
}

}  // namespace

TEST(OccupancyGridUtils, ConvertsWorldCoordinatesIntoGridCells)
{
  auto grid = makeGrid();
  unsigned int mx = 0;
  unsigned int my = 0;

  EXPECT_TRUE(evo_navigation::grid_utils::worldToMap(grid, 0.25, 0.35, mx, my));
  EXPECT_EQ(mx, 2U);
  EXPECT_EQ(my, 3U);

  EXPECT_FALSE(evo_navigation::grid_utils::worldToMap(grid, -0.01, 0.35, mx, my));
  EXPECT_FALSE(evo_navigation::grid_utils::worldToMap(grid, 1.20, 0.35, mx, my));
}

TEST(OccupancyGridUtils, ClassifiesUnknownOccupiedAndFreeMapCells)
{
  auto grid = makeGrid();
  grid.data[indexOf(grid, 2, 2)] = -1;
  grid.data[indexOf(grid, 3, 3)] = 80;

  using evo_navigation::grid_utils::CellStatus;
  EXPECT_EQ(
    evo_navigation::grid_utils::classifyMapCell(grid, 0.15, 0.15, 65),
    CellStatus::Free);
  EXPECT_EQ(
    evo_navigation::grid_utils::classifyMapCell(grid, 0.25, 0.25, 65),
    CellStatus::Unknown);
  EXPECT_EQ(
    evo_navigation::grid_utils::classifyMapCell(grid, 0.35, 0.35, 65),
    CellStatus::Occupied);
}

TEST(OccupancyGridUtils, ConvertsCostmapThresholdAndClassifiesHighCostCells)
{
  auto grid = makeGrid();
  grid.data[indexOf(grid, 4, 4)] = 99;

  using evo_navigation::grid_utils::CellStatus;
  EXPECT_EQ(evo_navigation::grid_utils::occupancyThresholdFromCostmapThreshold(253), 100);
  EXPECT_EQ(evo_navigation::grid_utils::occupancyThresholdFromCostmapThreshold(200), 79);
  EXPECT_EQ(
    evo_navigation::grid_utils::classifyCostmapCell(grid, 0.45, 0.45, 200),
    CellStatus::Occupied);
}

TEST(OccupancyGridUtils, ClearanceRejectsNearbyUnknownOrOccupiedCells)
{
  auto grid = makeGrid();
  std::string reason;

  EXPECT_TRUE(evo_navigation::grid_utils::hasClearance(grid, 0.50, 0.50, 0.10, 253, reason));

  grid.data[indexOf(grid, 5, 6)] = -1;
  EXPECT_FALSE(evo_navigation::grid_utils::hasClearance(grid, 0.50, 0.50, 0.15, 253, reason));
  EXPECT_EQ(reason, "rejected_unknown");

  grid.data[indexOf(grid, 5, 6)] = 0;
  grid.data[indexOf(grid, 6, 5)] = 100;
  EXPECT_FALSE(evo_navigation::grid_utils::hasClearance(grid, 0.50, 0.50, 0.15, 253, reason));
  EXPECT_EQ(reason, "rejected_occupied");
}
