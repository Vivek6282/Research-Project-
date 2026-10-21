/**
 * Trackside — Maps page (Admin and Driver; the Coach uses the Maps & Demo tab instead).
 *
 * Admin: add, archive, restore maps and edit corners; no Play button.
 * Driver: sees the maps read-only. The server enforces all of this as well.
 */

import { Link, Navigate } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import { TopBar } from "../../components/shell/top-bar";
import { Panel } from "../../components/ui/panel";
import { useAuth } from "../../lib/auth";
import { MapsBrowser } from "./components/maps-browser";

/** The Maps screen for Admin and Driver; a Coach is sent to the tab that has the same maps plus demo controls. */
export function MapsPage() {
  const { user } = useAuth();
  if (user?.role === "coach") return <Navigate to="/coach?tab=maps" replace />;
  const canManage = user?.role === "admin";

  return (
    <div className="min-h-screen" style={{ background: "var(--color-bg)" }}>
      <TopBar />
      <main className="max-w-[1400px] mx-auto px-3 sm:px-4 py-4 flex flex-col gap-4">
        <div className="flex items-center gap-3">
          <Link
            to={`/${user?.role ?? "login"}`}
            data-testid="maps-back-link"
            className="inline-flex items-center gap-1 text-[11px] font-mono text-[#7C8898] hover:text-[#3FA6E0]"
          >
            <ArrowLeft size={13} /> Dashboard
          </Link>
          <h1 className="text-sm font-mono uppercase tracking-widest text-[#E7EDF3]">Maps</h1>
        </div>
        <Panel title="Track maps">
          <MapsBrowser canManage={canManage} canEditCorners={canManage} />
        </Panel>
      </main>
    </div>
  );
}
