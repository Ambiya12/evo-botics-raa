import { describe, it, expect } from "vitest";
import type { ConnectionStatus } from "../admin";

describe("ConnectionStatus", () => {
  it("includes the 5 expected states", () => {
    const states: ConnectionStatus[] = [
      "mock",
      "connecting",
      "connected_ros",
      "disconnected",
      "error",
    ];
    expect(states).toHaveLength(5);
  });
});
