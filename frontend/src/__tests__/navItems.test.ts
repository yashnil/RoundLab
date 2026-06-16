import { APP_NAV_ITEMS, isNavItemActive } from "@/lib/navItems";

describe("APP_NAV_ITEMS", () => {
  it("includes an Evidence link pointing to /evidence", () => {
    const ev = APP_NAV_ITEMS.find((i) => i.label === "Evidence");
    expect(ev).toBeDefined();
    expect(ev?.href).toBe("/evidence");
  });

  it("has no duplicate Evidence entries", () => {
    const evs = APP_NAV_ITEMS.filter((i) => i.href === "/evidence");
    expect(evs.length).toBe(1);
  });

  it("includes Learn / Individual / Team / Evidence", () => {
    const labels = APP_NAV_ITEMS.map((i) => i.label);
    expect(labels).toEqual(expect.arrayContaining(["Learn", "Individual", "Team", "Evidence"]));
  });

  it("has unique hrefs (no duplicate nav items)", () => {
    const hrefs = APP_NAV_ITEMS.map((i) => i.href);
    expect(new Set(hrefs).size).toBe(hrefs.length);
  });
});

describe("isNavItemActive", () => {
  const ev = { href: "/evidence", label: "Evidence", match: ["/evidence"] };

  it("is active on /evidence", () => {
    expect(isNavItemActive(ev, "/evidence")).toBe(true);
  });

  it("is active on a nested evidence route", () => {
    expect(isNavItemActive(ev, "/evidence/builder")).toBe(true);
  });

  it("is not active on an unrelated route", () => {
    expect(isNavItemActive(ev, "/dashboard")).toBe(false);
  });

  it("handles null pathname", () => {
    expect(isNavItemActive(ev, null)).toBe(false);
  });
});
