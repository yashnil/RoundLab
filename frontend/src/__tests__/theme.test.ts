import {
  THEME_STORAGE_KEY,
  getStoredTheme,
  toggleTheme,
  setTheme,
} from "@/lib/theme";

describe("theme helpers (SSR-safe branches)", () => {
  it("exposes a stable storage key", () => {
    expect(THEME_STORAGE_KEY).toBe("roundlab-theme");
  });

  it("defaults to dark when there is no window", () => {
    // Runs under the node test environment: window is undefined.
    expect(typeof window).toBe("undefined");
    expect(getStoredTheme()).toBe("dark");
  });

  it("toggleTheme returns the opposite theme without throwing in SSR", () => {
    expect(toggleTheme("dark")).toBe("light");
    expect(toggleTheme("light")).toBe("dark");
  });

  it("setTheme is a no-op (does not throw) without a window", () => {
    expect(() => setTheme("light")).not.toThrow();
  });
});
