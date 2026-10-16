import { describe, it, expect, beforeEach, vi } from "vitest";
import { renderHook, act } from "@testing-library/react";
import React from "react";
import { AuthProvider, useAuth } from "./AuthContext";

describe("AuthContext", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });

  const wrapper = ({ children }: { children: React.ReactNode }) => (
    <AuthProvider>{children}</AuthProvider>
  );

  it("initializes with unauthenticated state when localStorage is empty", () => {
    const { result } = renderHook(() => useAuth(), { wrapper });
    expect(result.current.isAuthenticated).toBe(false);
    expect(result.current.user).toBeNull();
    expect(result.current.token).toBeNull();
    expect(result.current.isLoading).toBe(false);
  });

  it("rehydrates user and token from localStorage", () => {
    const user = { id: "u123", email: "stored@test.com", full_name: "Stored User" };
    localStorage.setItem("mt_token", "stored-token-abc");
    localStorage.setItem("mt_user", JSON.stringify(user));

    const { result } = renderHook(() => useAuth(), { wrapper });
    expect(result.current.isAuthenticated).toBe(true);
    expect(result.current.token).toBe("stored-token-abc");
    expect(result.current.user).toEqual(user);
  });

  it("updates state and persists to localStorage on login", () => {
    const { result } = renderHook(() => useAuth(), { wrapper });
    const user = { id: "u456", email: "new@test.com", full_name: "New User" };

    act(() => {
      result.current.login("token-xyz", user);
    });

    expect(result.current.isAuthenticated).toBe(true);
    expect(result.current.token).toBe("token-xyz");
    expect(result.current.user).toEqual(user);
    expect(localStorage.getItem("mt_token")).toBe("token-xyz");
    expect(JSON.parse(localStorage.getItem("mt_user") || "{}")).toEqual(user);
  });

  it("clears state and removes from localStorage on logout", () => {
    const user = { id: "u789", email: "logout@test.com", full_name: "Logout User" };
    localStorage.setItem("mt_token", "token-to-remove");
    localStorage.setItem("mt_user", JSON.stringify(user));

    const { result } = renderHook(() => useAuth(), { wrapper });
    expect(result.current.isAuthenticated).toBe(true);

    act(() => {
      result.current.logout();
    });

    expect(result.current.isAuthenticated).toBe(false);
    expect(result.current.token).toBeNull();
    expect(result.current.user).toBeNull();
    expect(localStorage.getItem("mt_token")).toBeNull();
    expect(localStorage.getItem("mt_user")).toBeNull();
  });

  it("updates user fields via updateUser", () => {
    const user = { id: "u100", email: "edit@test.com", full_name: "Old Name" };
    localStorage.setItem("mt_token", "token-edit");
    localStorage.setItem("mt_user", JSON.stringify(user));

    const { result } = renderHook(() => useAuth(), { wrapper });

    act(() => {
      result.current.updateUser({ full_name: "New Name" });
    });

    expect(result.current.user?.full_name).toBe("New Name");
    expect(result.current.user?.email).toBe("edit@test.com");
    expect(JSON.parse(localStorage.getItem("mt_user") || "{}").full_name).toBe("New Name");
  });

  it("throws error when useAuth is called outside AuthProvider", () => {
    // Suppress React error boundary console log for this expected error
    const spy = vi.spyOn(console, "error").mockImplementation(() => {});
    expect(() => renderHook(() => useAuth())).toThrow("useAuth must be used inside <AuthProvider>");
    spy.mockRestore();
  });
});
