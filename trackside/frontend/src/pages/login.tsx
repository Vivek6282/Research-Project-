/**
 * Trackside — Login Page (Pit-Wall Access)
 *
 * Slanted Go-Karting Vehicle Background Banners (-12deg slant):
 * - Slanted top & bottom filmstrips carrying actual go-kart racing photos & kart graphics
 * - Continuous infinite horizontal scrolling animation
 * - Radial dark vignette overlay for legibility
 * - 5-segment LED signal strip top accent
 * - T R A C K S I D E title & DRIVER SAFETY & PERFORMANCE · V2.4.1 version badge
 * - Pit-Wall Access card with Motorsport Hazard Stripe top border
 * - System Online status badge
 * - Role Switcher tabs (COACH / ADMIN / DRIVER)
 * - Name/Email & Access Code inputs
 * - Full-width cyan-blue SIGN IN button
 * - © 2026 APEX SYSTEMS page footer
 */

import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../lib/auth";

const LED_COLORS = ["#33D17E", "#33D17E", "#F2A93B", "#F2A93B", "#E5473C"];

// Authentic Go-Karting Vehicles & Kart Race Imagery from Unsplash & Local Assets
const KART_IMAGES_SET_A = [
  "/images/kart5.jpg", // User yellow kart photo (https://images.unsplash.com/photo-1695227667420-6af83966b3bf)
  "/images/kart1.jpg",
  "/images/kart2.jpg",
  "/images/kart6.jpg",
  "/images/kart3.jpg",
  "/images/kart4.jpg",
];

const KART_IMAGES_SET_B = [
  "/images/kart2.jpg",
  "/images/kart6.jpg",
  "/images/kart5.jpg",
  "/images/kart4.jpg",
  "/images/kart1.jpg",
  "/images/kart3.jpg",
];

export function LoginPage() {
  const { login, error, clearError } = useAuth();
  const navigate = useNavigate();

  const [selectedRole, setSelectedRole] = useState<"coach" | "admin" | "driver">("coach");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const DEMO_EMAILS = {
    admin: "admin@trackside.local",
    coach: "coach@trackside.local",
    driver: "driver@trackside.local",
  };

  const handleRoleSelect = (role: "coach" | "admin" | "driver") => {
    setSelectedRole(role);
    if (!email || Object.values(DEMO_EMAILS).includes(email)) {
      setEmail(DEMO_EMAILS[role]);
    }
  };

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (isSubmitting) return;

    clearError();
    setIsSubmitting(true);

    const loginEmail = email || DEMO_EMAILS[selectedRole];

    try {
      const user = await login(loginEmail, password);
      navigate(`/${user.role}`, { replace: true });
    } catch {
      // Handled in auth context
    } finally {
      setIsSubmitting(false);
    }
  }

  // Duplicate image arrays once to guarantee a seamless -50% ↔ 0% loop over 34s
  const col1 = [...KART_IMAGES_SET_A, ...KART_IMAGES_SET_A];
  const col2 = [...KART_IMAGES_SET_B, ...KART_IMAGES_SET_B];
  const col3 = [...KART_IMAGES_SET_A, ...KART_IMAGES_SET_A].reverse();
  const col4 = [...KART_IMAGES_SET_B, ...KART_IMAGES_SET_B].reverse();

  return (
    <div className="relative min-h-screen flex flex-col items-center justify-center px-4 py-8 select-none bg-[#0A0E13] text-[#E7EDF3] overflow-hidden">
      {/* 
        Full-Bleed Animated Background:
        - 4 vertical columns inside a rotated (-16°) oversized wrapper (160%)
        - Continuous 34s linear drift loop (alternating downward & upward)
        - 3:4 portrait tiles with light desaturation & contrast
      */}
      <div className="bg-slanted-grid-wrapper">
        {/* Column 1: Drift Downward */}
        <div className="grid-column column-drift-down">
          {col1.map((src, i) => (
            <img
              key={`c1-${i}`}
              src={src}
              alt="Go-Kart Racing"
              className="grid-photo-tile"
              loading="lazy"
            />
          ))}
        </div>

        {/* Column 2: Drift Upward */}
        <div className="grid-column column-drift-up">
          {col2.map((src, i) => (
            <img
              key={`c2-${i}`}
              src={src}
              alt="Kart Circuit"
              className="grid-photo-tile"
              loading="lazy"
            />
          ))}
        </div>

        {/* Column 3: Drift Downward */}
        <div className="grid-column column-drift-down">
          {col3.map((src, i) => (
            <img
              key={`c3-${i}`}
              src={src}
              alt="Telemetry Kart"
              className="grid-photo-tile"
              loading="lazy"
            />
          ))}
        </div>

        {/* Column 4: Drift Upward */}
        <div className="grid-column column-drift-up">
          {col4.map((src, i) => (
            <img
              key={`c4-${i}`}
              src={src}
              alt="Racing Go-Kart"
              className="grid-photo-tile"
              loading="lazy"
            />
          ))}
        </div>
      </div>

      {/* Legibility Radial Scrim Overlay */}
      <div className="bg-radial-scrim" />

      {/* Main Form Container (Max-Width 330px) */}
      <div className="relative z-10 w-full max-w-[330px] flex flex-col items-center animate-fade-in">
        {/* 5-Segment Green → Amber → Red Signal Strip */}
        <div className="flex items-center gap-1.5 mb-4">
          {LED_COLORS.map((color, i) => (
            <div
              key={i}
              className="w-4 h-2.5 rounded-[1px]"
              style={{
                background: color,
                boxShadow: `0 0 8px ${color}88`,
              }}
            />
          ))}
        </div>

        {/* Wordmark "TRACKSIDE" & Subtitle */}
        <h1
          className="text-xl font-bold tracking-[0.35em] text-center mb-1 uppercase font-sans text-[#E7EDF3]"
        >
          TRACKSIDE
        </h1>
        <p
          className="text-[9px] font-mono tracking-[0.15em] text-center mb-5 uppercase text-[#7C8898]"
        >
          DRIVER SAFETY & PERFORMANCE · V2.4.1
        </p>

        {/* Flat Panel Login Card (Max-Width 330px, 2px radius, Kerb Stripe Top Border) */}
        <div
          className="w-full rounded-[2px] overflow-hidden relative shadow-2xl"
          style={{
            background: "#12181F",
            border: "1px solid #232B35",
            boxShadow: "0 20px 45px rgba(0,0,0,0.85)",
          }}
        >
          {/* Red/White Diagonal Kerb Stripe Top Edge */}
          <div className="w-full h-[3px] hazard-stripe" />

          <div className="p-5">
            {/* Card Header: PIT-WALL ACCESS & SYSTEM ONLINE */}
            <div className="flex items-center justify-between mb-4">
              <span className="text-[10px] font-mono uppercase tracking-widest font-semibold text-[#7C8898]">
                PIT-WALL ACCESS
              </span>
              <div className="flex items-center gap-1 px-1.5 py-0.5 rounded-[2px] text-[9px] font-mono tracking-wider text-[#33D17E] bg-[#33D17E]/10 border border-[#33D17E]/30">
                <span className="w-1.5 h-1.5 rounded-full bg-[#33D17E] animate-pulse" />
                SYSTEM ONLINE
              </div>
            </div>

            {/* Error Banner */}
            {error && (
              <div className="rounded-[2px] px-3 py-1.5 mb-3 text-[11px] font-mono bg-[#E5473C]/15 border border-[#E5473C]/40 text-[#E5473C]">
                {error}
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-3.5">
              {/* Segmented Role Selector */}
              <div>
                <label className="block text-[9px] font-mono uppercase tracking-wider mb-1 text-[#7C8898]">
                  ROLE
                </label>
                <div className="grid grid-cols-3 gap-0 rounded-[2px] overflow-hidden p-0.5 bg-[#161D26] border border-[#232B35]">
                  {(["coach", "admin", "driver"] as const).map((role) => {
                    const isActive = selectedRole === role;
                    return (
                      <button
                        key={role}
                        type="button"
                        onClick={() => handleRoleSelect(role)}
                        className="py-1.5 text-[10px] font-sans font-bold uppercase tracking-wider transition-all duration-150 rounded-[2px] cursor-pointer"
                        style={{
                          background: isActive ? "#3FA6E0" : "transparent",
                          color: isActive ? "#ffffff" : "#7C8898",
                        }}
                      >
                        {role}
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Name Text Field */}
              <div>
                <label className="block text-[9px] font-mono uppercase tracking-wider mb-1 text-[#7C8898]">
                  NAME
                </label>
                <input
                  type="text"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="Full name"
                  required
                  className="w-full px-3 py-2 rounded-[2px] text-xs font-sans outline-none transition-colors bg-[#0A0E13] border border-[#232B35] text-[#E7EDF3] placeholder-[#4B5563] focus:border-[#3FA6E0]"
                />
              </div>

              {/* Monospace Access Code Field */}
              <div>
                <label className="block text-[9px] font-mono uppercase tracking-wider mb-1 text-[#7C8898]">
                  ACCESS CODE
                </label>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  required
                  className="w-full px-3 py-2 rounded-[2px] text-xs font-mono outline-none transition-colors bg-[#0A0E13] border border-[#232B35] text-[#E7EDF3] placeholder-[#4B5563] focus:border-[#3FA6E0]"
                />
              </div>

              {/* Primary Electric Blue Sign In Button */}
              <button
                type="submit"
                disabled={isSubmitting}
                className="w-full py-2.5 rounded-[2px] text-xs font-bold font-sans uppercase tracking-wider transition-colors cursor-pointer disabled:opacity-50 mt-1 shadow-md bg-[#3FA6E0] text-white hover:bg-[#3595cb]"
              >
                {isSubmitting ? "AUTHENTICATING…" : "SIGN IN"}
              </button>
            </form>

            {/* Muted Helper Line */}
            <p className="text-center text-[10px] font-sans text-[#7C8898] mt-3">
              Contact your academy administrator for credentials.
            </p>
          </div>
        </div>

        {/* Muted Monospace Page Footer */}
        <p className="text-center text-[9px] font-mono tracking-widest text-[#4B5563] mt-5 uppercase">
          © 2026 APEX SYSTEMS
        </p>
      </div>
    </div>
  );
}
