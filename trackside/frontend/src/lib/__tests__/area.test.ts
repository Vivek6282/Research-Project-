/**
 * Trackside — role areas: which sign-in a page and its requests belong to.
 */

import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { api } from "../api";
import { areaFromPath, currentArea, forgetArea, rememberArea, withArea } from "../area";

/** Pretend the page is at this path. */
function openPage(path: string) {
  window.history.pushState({}, "", path);
}

describe("area of a page", () => {
  beforeEach(() => { window.sessionStorage.clear(); openPage("/"); });

  it("a module's own address names its area", () => {
    expect(areaFromPath("/driver")).toBe("driver");
    expect(areaFromPath("/coach")).toBe("coach");
    expect(areaFromPath("/admin/users")).toBe("admin");
    expect(areaFromPath("/maps")).toBeNull();
    expect(areaFromPath("/login")).toBeNull();
    expect(areaFromPath("/drivers-fake")).toBeNull();
  });

  it("the module address wins over what this tab remembered", () => {
    rememberArea("coach");
    openPage("/driver");
    expect(currentArea()).toBe("driver");
  });

  it("a shared page such as /maps uses the area this tab signed in with, and none before that", () => {
    openPage("/maps");
    expect(currentArea()).toBeNull();
    rememberArea("coach");
    expect(currentArea()).toBe("coach");
    forgetArea();
    expect(currentArea()).toBeNull();
  });

  it("only real roles are remembered", () => {
    rememberArea("superuser");
    openPage("/maps");
    expect(currentArea()).toBeNull();
  });

  it("live feed addresses get the page's area, and are left alone when there is none", () => {
    openPage("/driver");
    expect(withArea("ws://h/ws/sessions/1/telemetry/")).toBe("ws://h/ws/sessions/1/telemetry/?area=driver");
    expect(withArea("ws://h/x?y=1")).toBe("ws://h/x?y=1&area=driver");
    openPage("/login");
    expect(withArea("ws://h/ws/a/")).toBe("ws://h/ws/a/");
  });
});

describe("area header on requests", () => {
  const seen: Record<string, string>[] = [];

  beforeEach(() => {
    seen.length = 0;
    window.sessionStorage.clear();
    vi.stubGlobal("fetch", vi.fn(async (_url: string, init: RequestInit) => {
      seen.push({ ...(init.headers as Record<string, string>) });
      return new Response(JSON.stringify({}), { status: 200, headers: { "Content-Type": "application/json" } });
    }));
  });
  afterEach(() => vi.unstubAllGlobals());

  it("a driver page sends the driver area, a coach page the coach area", async () => {
    openPage("/driver");
    await api.get("/api/auth/me/");
    openPage("/coach");
    await api.get("/api/auth/me/");
    expect(seen.map((h) => h["X-Trackside-Area"])).toEqual(["driver", "coach"]);
  });

  it("the login request asks for 'auto' whatever page it is sent from", async () => {
    openPage("/driver");
    await api.post("/api/auth/login/", { identifier: "x", password: "y" });
    expect(seen[0]["X-Trackside-Area"]).toBe("auto");
  });

  it("a page with no area (and nothing remembered) sends no area header", async () => {
    openPage("/login");
    await api.get("/api/auth/me/");
    expect(seen[0]["X-Trackside-Area"]).toBeUndefined();
  });

  it("a shared page sends the area this tab signed in with", async () => {
    rememberArea("admin");
    openPage("/maps");
    await api.get("/api/tracks/");
    expect(seen[0]["X-Trackside-Area"]).toBe("admin");
  });
});
