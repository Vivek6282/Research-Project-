/**
 * Trackside — Session notice banner.
 * Tells the person why this tab changed account by itself. All tabs of one browser share one sign-in, so
 * signing in as someone else in another tab changes this tab too. Two roles at once need two browsers.
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
      <span>
        {sessionNotice} Tabs of one browser share one sign-in. To use two roles at the same time, open a private
        window or a second browser.
      </span>
      <button onClick={dismissSessionNotice} className="px-2 py-0.5 border border-[#F2A93B66] rounded-[2px] cursor-pointer">
        Dismiss
      </button>
    </div>
  );
}
