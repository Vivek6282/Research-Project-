/**
 * Trackside — Login Page (Pit-Wall Access).
 * Displays animated full-bleed go-kart filmstrip background,
 * LED status signals, brand typography, and the LoginForm card.
 */

import { LoginForm } from "../components/login/login-form";

const LED_COLORS = ["#33D17E", "#33D17E", "#F2A93B", "#F2A93B", "#E5473C"];

const KART_IMAGES_SET_A = [
  "/images/kart5.jpg",
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
  const columnOneImages = [...KART_IMAGES_SET_A, ...KART_IMAGES_SET_A];
  const columnTwoImages = [...KART_IMAGES_SET_B, ...KART_IMAGES_SET_B];
  const columnThreeImages = [...KART_IMAGES_SET_A, ...KART_IMAGES_SET_A].reverse();
  const columnFourImages = [...KART_IMAGES_SET_B, ...KART_IMAGES_SET_B].reverse();

  return (
    <div className="relative min-h-screen flex flex-col items-center justify-center px-4 py-8 select-none bg-[#0A0E13] text-[#E7EDF3] overflow-hidden">
      {/* Full-Bleed Animated Background Filmstrips */}
      <div className="bg-slanted-grid-wrapper">
        <div className="grid-column column-drift-down">
          {columnOneImages.map((imageSrc, index) => (
            <img
              key={`c1-${index}`}
              src={imageSrc}
              alt="Go-Kart Racing"
              className="grid-photo-tile"
              loading="lazy"
            />
          ))}
        </div>

        <div className="grid-column column-drift-up">
          {columnTwoImages.map((imageSrc, index) => (
            <img
              key={`c2-${index}`}
              src={imageSrc}
              alt="Kart Circuit"
              className="grid-photo-tile"
              loading="lazy"
            />
          ))}
        </div>

        <div className="grid-column column-drift-down">
          {columnThreeImages.map((imageSrc, index) => (
            <img
              key={`c3-${index}`}
              src={imageSrc}
              alt="Telemetry Kart"
              className="grid-photo-tile"
              loading="lazy"
            />
          ))}
        </div>

        <div className="grid-column column-drift-up">
          {columnFourImages.map((imageSrc, index) => (
            <img
              key={`c4-${index}`}
              src={imageSrc}
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
          {LED_COLORS.map((ledColor, index) => (
            <div
              key={index}
              className="w-4 h-2.5 rounded-[1px]"
              style={{
                background: ledColor,
                boxShadow: `0 0 8px ${ledColor}88`,
              }}
            />
          ))}
        </div>

        {/* Wordmark "TRACKSIDE" & Subtitle */}
        <h1 className="text-xl font-bold tracking-[0.35em] text-center mb-1 uppercase font-sans text-[#E7EDF3]">
          TRACKSIDE
        </h1>
        <p className="text-[9px] font-mono tracking-[0.15em] text-center mb-5 uppercase text-[#7C8898]">
          DRIVER SAFETY & PERFORMANCE · V2.4.1
        </p>

        {/* Modular Login Form */}
        <LoginForm />

        {/* Muted Monospace Page Footer */}
        <p className="text-center text-[9px] font-mono tracking-widest text-[#4B5563] mt-5 uppercase">
          © 2026 TRACKSIDE
        </p>
      </div>
    </div>
  );
}
