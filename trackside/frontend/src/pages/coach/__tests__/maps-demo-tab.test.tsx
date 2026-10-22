/**
 * Trackside Coach — the Maps & Demo tab opens from the ?tab=maps link and the top bar points to it (H1).
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { Link, MemoryRouter } from "react-router-dom";

vi.mock("../../../lib/api", () => ({ api: { get: vi.fn(), post: vi.fn(), delete: vi.fn(), upload: vi.fn() } }));
const authState: { user: { role: string; name: string } | null } = { user: { role: "coach", name: "Coach" } };
vi.mock("../../../lib/auth", () => ({ useAuth: () => ({ ...authState, logout: vi.fn() }) }));
vi.mock("../../../context/PreferencesContext", () => ({ usePreferences: () => ({ openSettings: vi.fn() }) }));
vi.mock("../../../components/ui/settings-modal", () => ({ SettingsModal: () => null }));

import { api } from "../../../lib/api";
import { TopBar } from "../../../components/shell/top-bar";
import { useCoachTab } from "../hooks/use-coach-tab";
import { MapsDemoTab } from "../components/maps-demo-tab";

/** Show which tab the hook says is open, plus a link to the maps tab. */
function TabHarness() {
  const { activeTab } = useCoachTab();
  return (
    <div>
      <span data-testid="tab">{activeTab}</span>
      <Link to="/coach?tab=maps" data-testid="go-maps">go</Link>
    </div>
  );
}

describe("useCoachTab", () => {
  it("starts on Live and on Maps when the link says tab=maps", () => {
    const { unmount } = render(<MemoryRouter initialEntries={["/coach"]}><TabHarness /></MemoryRouter>);
    expect(screen.getByTestId("tab").textContent).toBe("live");
    unmount();
    render(<MemoryRouter initialEntries={["/coach?tab=maps"]}><TabHarness /></MemoryRouter>);
    expect(screen.getByTestId("tab").textContent).toBe("maps");
  });

  it("follows the link when the Coach screen is already open", () => {
    render(<MemoryRouter initialEntries={["/coach"]}><TabHarness /></MemoryRouter>);
    fireEvent.click(screen.getByTestId("go-maps"));
    expect(screen.getByTestId("tab").textContent).toBe("maps");
  });
});

describe("Top bar Maps link", () => {
  it("points a coach to the tab and everyone else to /maps", () => {
    authState.user = { role: "coach", name: "Coach" };
    const { unmount } = render(<MemoryRouter><TopBar /></MemoryRouter>);
    expect(screen.getByTestId("topbar-maps-link").getAttribute("href")).toBe("/coach?tab=maps");
    unmount();
    for (const role of ["admin", "driver"]) {
      authState.user = { role, name: role };
      const view = render(<MemoryRouter><TopBar /></MemoryRouter>);
      expect(screen.getByTestId("topbar-maps-link").getAttribute("href")).toBe("/maps");
      view.unmount();
    }
  });
});

describe("MapsDemoTab", () => {
  beforeEach(() => {
    vi.mocked(api.get).mockResolvedValue({ results: [{ id: "d", name: "Demo Circuit", source: "builtin", is_builtin: true, is_archived: false, zones: [] }] });
    vi.mocked(api.post).mockResolvedValue({});
  });

  it("shows the maps with Add track for a coach", async () => {
    render(<MemoryRouter><MapsDemoTab onWatchLive={vi.fn()} /></MemoryRouter>);
    await waitFor(() => expect(screen.getByTestId("map-card-Demo Circuit")).toBeTruthy());
    expect(screen.getByTestId("add-map-btn").textContent).toContain("Add track");
  });
});
