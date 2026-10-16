import { describe, it, expect, beforeEach } from "vitest";
import { sessionStore } from "./sessionStore";

describe("sessionStore", () => {
  beforeEach(() => {
    sessionStore.camStream = null;
    sessionStore.screenStream = null;
    sessionStore.micOn = false;
    sessionStore.camOn = false;
  });

  it("initializes with default values", () => {
    expect(sessionStore.camStream).toBeNull();
    expect(sessionStore.screenStream).toBeNull();
    expect(sessionStore.micOn).toBe(false);
    expect(sessionStore.camOn).toBe(false);
  });

  it("updates device state accurately", () => {
    sessionStore.micOn = true;
    sessionStore.camOn = true;
    expect(sessionStore.micOn).toBe(true);
    expect(sessionStore.camOn).toBe(true);
  });

  it("holds media streams across consumer reads", () => {
    const dummyStream = {} as MediaStream;
    sessionStore.camStream = dummyStream;
    expect(sessionStore.camStream).toBe(dummyStream);
  });
});
