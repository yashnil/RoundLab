import {
  APP_NAV_GROUPS,
  flattenNavGroups,
  isNavItemActive,
} from "@/lib/navItems";

describe("APP_NAV_GROUPS", () => {
  it("exposes the Train / Research / Team / Resources groups", () => {
    const ids = APP_NAV_GROUPS.map((g) => g.id);
    expect(ids).toEqual(["train", "research", "team", "resources"]);
  });

  it("places the primary training destinations in Train", () => {
    const train = APP_NAV_GROUPS.find((g) => g.id === "train");
    const hrefs = train?.items.map((i) => i.href);
    expect(hrefs).toEqual(["/dashboard", "/session", "/progress", "/learn"]);
  });

  it("gives every item an icon, a label, and at least one match prefix", () => {
    for (const group of APP_NAV_GROUPS) {
      for (const item of group.items) {
        expect(item.icon).toBeDefined();
        expect(item.label.length).toBeGreaterThan(0);
        expect(item.match.length).toBeGreaterThan(0);
      }
    }
  });

  it("has no duplicate hrefs across groups", () => {
    const hrefs = APP_NAV_GROUPS.flatMap((g) => g.items.map((i) => i.href));
    expect(new Set(hrefs).size).toBe(hrefs.length);
  });
});

describe("flattenNavGroups", () => {
  it("returns every non-coach item by default", () => {
    const items = flattenNavGroups();
    const totalNonCoach = APP_NAV_GROUPS.flatMap((g) => g.items).filter(
      (i) => !i.coachOnly,
    ).length;
    expect(items.length).toBe(totalNonCoach);
  });

  it("includes coach-only items only when isCoach is true", () => {
    const withoutCoach = flattenNavGroups({ isCoach: false });
    const withCoach = flattenNavGroups({ isCoach: true });
    expect(withCoach.length).toBeGreaterThanOrEqual(withoutCoach.length);
  });
});

describe("isNavItemActive on sidebar items", () => {
  it("marks Practice active on a nested /speech route", () => {
    const train = APP_NAV_GROUPS.find((g) => g.id === "train")!;
    const practice = train.items.find((i) => i.label === "Practice")!;
    expect(isNavItemActive(practice, "/speech/abc123")).toBe(true);
    expect(isNavItemActive(practice, "/session")).toBe(true);
    expect(isNavItemActive(practice, "/evidence")).toBe(false);
  });

  it("marks Drills & Learn active on a nested /drills route", () => {
    const train = APP_NAV_GROUPS.find((g) => g.id === "train")!;
    const learn = train.items.find((i) => i.label === "Drills & Learn")!;
    expect(isNavItemActive(learn, "/drills/xyz")).toBe(true);
    expect(isNavItemActive(learn, "/learn")).toBe(true);
  });
});
