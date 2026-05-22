import { describe, it, expect, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import "fake-indexeddb/auto";
import { db } from "../../services/timeSeriesStore";
import { useTimeSeriesData } from "../useTimeSeriesData";

beforeEach(async () => {
  await db.metrics.clear();
});

describe("useTimeSeriesData", () => {
  it("returns empty array when no data exists", () => {
    const { result } = renderHook(() => useTimeSeriesData("battery", 15));
    expect(result.current).toEqual([]);
  });

  it("returns only points within the given window", async () => {
    const now = Date.now();
    await db.metrics.bulkAdd([
      { timestamp: now - 1_000, metric: "battery", value: 80 },
      { timestamp: now - 30 * 60 * 1000, metric: "battery", value: 60 },
    ]);
    const { result } = renderHook(() => useTimeSeriesData("battery", 15));
    await waitFor(() => {
      expect(result.current).toHaveLength(1);
    });
    expect(result.current[0].value).toBe(80);
  });

  it("does not return points from another metric", async () => {
    const now = Date.now();
    await db.metrics.bulkAdd([
      { timestamp: now - 1_000, metric: "latency", value: 42 },
    ]);
    const { result } = renderHook(() => useTimeSeriesData("battery", 15));
    await waitFor(() => {
      expect(result.current).toHaveLength(0);
    });
  });
});
