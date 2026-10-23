/**
 * Trackside — Session notice banner.
 * Tells the person why this tab changed account by itself. Each role (admin, coach, driver) has its own sign-in
 * in the browser, so a driver tab and a coach tab do not affect each other. This appears only when the SAME role
 * was signed in or out in another tab (for example a second coach account, or a sign-out in another coach tab).
 */

import { useAuth } from "../../lib/auth";

export function SessionNoticeBanner() {
  const { sessionNotice, dismissSessionNotice } = useAuth();
  if (!sessionNotice) return null;
  return (
    <div
      role="alert"
      data-testid="session-notice"
      className="fixed top-0 inset-x-0 z-50 flex items-center justify-between gap-3 px-4 py-2 text-xs font-mono border-b border-[#F2A93B66] bg-[#2A2210] text-[#F2A93B]"
    >
      <span>{sessionNotice}</span>
      <button onClick={dismissSessionNotice} className="px-2 py-0.5 border border-[#F2A93B66] rounded-[2px] cursor-pointer">
        Dismiss
      </button>
    </div>
  );
}
