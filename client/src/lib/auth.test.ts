import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { authApi } from "./auth";

describe("authApi", () => {
  const originalFetch = global.fetch;

  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    global.fetch = originalFetch;
  });

  describe("login", () => {
    it("returns LoginResponse on successful credentials", async () => {
      const mockResponse = {
        access_token: "jwt-test-token",
        token_type: "bearer",
        user: { id: "u1", email: "student@test.com", full_name: "Alice" },
      };

      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: async () => mockResponse,
      } as Response);

      const res = await authApi.login("student@test.com", "Password123!");
      expect(res.access_token).toBe("jwt-test-token");
      expect(res.user.email).toBe("student@test.com");
      expect(global.fetch).toHaveBeenCalledWith("/api/auth/login", expect.objectContaining({
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: "student@test.com", password: "Password123!" }),
      }));
    });

    it("throws an error with message from server on 401 response", async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 401,
        json: async () => ({ detail: "Invalid email or password" }),
      } as Response);

      await expect(authApi.login("student@test.com", "wrongpass")).rejects.toThrow("Invalid email or password");
    });
  });

  describe("register", () => {
    it("sends registration data and returns success", async () => {
      const mockResult = { message: "Check email", email: "new@test.com" };

      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: async () => mockResult,
      } as Response);

      const res = await authApi.register("new@test.com", "Secret123!", "New Student");
      expect(res.email).toBe("new@test.com");
      expect(global.fetch).toHaveBeenCalledWith("/api/auth/register", expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ email: "new@test.com", password: "Secret123!", full_name: "New Student" }),
      }));
    });
  });

  describe("updateProfile", () => {
    it("sends PATCH with Authorization header", async () => {
      const updatedUser = { id: "u1", email: "u@test.com", full_name: "Alice Updated" };

      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: async () => updatedUser,
      } as Response);

      const res = await authApi.updateProfile("test-token", { full_name: "Alice Updated" });
      expect(res.full_name).toBe("Alice Updated");
      expect(global.fetch).toHaveBeenCalledWith("/api/auth/profile", expect.objectContaining({
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          Authorization: "Bearer test-token",
        },
        body: JSON.stringify({ full_name: "Alice Updated" }),
      }));
    });
  });
});
