import React, { useState, useEffect, useRef, useCallback } from "react";
import { LineChart, Line, ResponsiveContainer, YAxis } from "recharts";
import { Play, Pause, RotateCcw, Gauge, ShieldAlert, Radio, Info } from "lucide-react";

// ---------- design tokens (matches Trackside) ----------
const C = {
  bg: "#0A0E13",
  panel: "#12181F",
  panel2: "#161D26",
  line: "#232B35",
  text: "#E7EDF3",
  muted: "#7C8898",
  faint: "#4B5563",
  green: "#33D17E",
  amber: "#F2A93B",
  red: "#E5473C",
  blue: "#3FA6E0",
};

// zones defined as fractions along the track path [start, end], plus base clean-lap g and alert threshold
const ZONES = [
  { id: "z1", label: "Hairpin", range: [0.14, 0.30], base: 0.95, threshold: 1.15 },
  { id: "z2", label: "Sweeper", range: [0.42, 0.62], base: 1.30, threshold: 1.55 },
  { id: "z3", label: "Chicane", range: [0.74, 0.88], base: 1.05, threshold: 1.30 },
];

const LAP_SECONDS = 11;

function getZoneAt(t) {
  return ZONES.find((z) => t >= z.range[0] && t <= z.range[1]) || null;
}

function stageFor(g, threshold) {
  if (g >= threshold) return "red";
  if (g >= threshold * 0.82) return "amber";
  return "green";
}

const STAGE_META = {
  green: { label: "ON LINE", color: C.green },
  amber: { label: "APPROACHING LIMIT", color: C.amber },
  red: { label: "THRESHOLD EXCEEDED", color: C.red },
};

function SignalStrip({ stage }) {
  const order = ["green", "green", "amber", "amber", "red"];
  const activeCount = stage === "green" ? 2 : stage === "amber" ? 4 : 5;
  return (
    <div className="flex items-center gap-1">
      {order.map((c, i) => {
        const lit = i < activeCount;
        return (
          <div
            key={i}
            style={{
              width: 20,
              height: 12,
              borderRadius: 2,
              background: lit ? STAGE_META[c].color : C.line,
              boxShadow: lit ? `0 0 8px ${STAGE_META[c].color}88` : "none",
              transition: "all 150ms ease",
            }}
          />
        );
      })}
    </div>
  );
}

function Panel({ title, icon: Icon, right, children }) {
  return (
    <div className="rounded-lg p-4" style={{ background: C.panel, border: `1px solid ${C.line}` }}>
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          {Icon && <Icon size={15} style={{ color: C.muted }} />}
          <h3 className="text-xs font-mono uppercase tracking-widest" style={{ color: C.muted }}>{title}</h3>
        </div>
        {right}
      </div>
      {children}
    </div>
  );
}

// Track path (SVG) - oval with hairpin, sweeper bulge, chicane kink
const TRACK_PATH =
  "M 60,180 C 60,90 130,40 230,40 C 320,40 340,90 300,120 C 270,143 250,120 230,140 " +
  "C 205,165 240,190 290,190 C 380,190 420,150 420,100 C 420,55 385,30 330,30 " +
  "C 300,30 300,10 340,10 C 420,10 460,60 460,120 C 460,200 400,260 300,260 " +
  "C 180,260 60,270 60,180 Z";

export default function KartingSimulation() {
  const pathRef = useRef(null);
  const [totalLen, setTotalLen] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [t, setT] = useState(0);
  const [aggression, setAggression] = useState(1.0);
  const [point, setPoint] = useState({ x: 60, y: 180 });
  const [gHistory, setGHistory] = useState(Array.from({ length: 30 }, (_, i) => ({ i, g: 0.3 })));
  const [alertLog, setAlertLog] = useState([]);
  const lastStageRef = useRef({});
  const rafRef = useRef(null);
  const startRef = useRef(null);

  useEffect(() => {
    if (pathRef.current) setTotalLen(pathRef.current.getTotalLength());
  }, []);

  const computeG = useCallback(
    (tt) => {
      const zone = getZoneAt(tt);
      if (!zone) return { g: 0.25 + Math.random() * 0.08, zone: null };
      const [s, e] = zone.range;
      const local = (tt - s) / (e - s);
      const shape = Math.sin(Math.PI * local); // 0 at edges, 1 at middle
      const noise = (Math.random() - 0.5) * 0.05;
      const g = zone.base * aggression * shape + 0.15 + noise;
      return { g: Math.max(0, g), zone };
    },
    [aggression]
  );

  const tick = useCallback(
    (ts) => {
      if (startRef.current == null) startRef.current = ts;
      const elapsed = (ts - startRef.current) / 1000;
      let tt = (elapsed % LAP_SECONDS) / LAP_SECONDS;
      setT(tt);

      if (pathRef.current && totalLen) {
        const p = pathRef.current.getPointAtLength(tt * totalLen);
        setPoint({ x: p.x, y: p.y });
      }

      const { g, zone } = computeG(tt);
      setGHistory((h) => [...h.slice(1), { i: h[h.length - 1].i + 1, g: Number(g.toFixed(2)) }]);

      const threshold = zone ? zone.threshold : 999;
      const stage = zone ? stageFor(g, threshold) : "green";
      const key = zone ? zone.id : "straight";
      if (zone && stage === "red" && lastStageRef.current[key] !== "red") {
        setAlertLog((log) => [
          {
            time: new Date().toLocaleTimeString(),
            text: `${zone.label} — threshold exceeded (${g.toFixed(2)}g > ${zone.threshold}g)`,
          },
          ...log.slice(0, 7),
        ]);
      }
      lastStageRef.current[key] = stage;

      rafRef.current = requestAnimationFrame(tick);
    },
    [computeG, totalLen]
  );

  useEffect(() => {
    if (playing) {
      startRef.current = null;
      rafRef.current = requestAnimationFrame(tick);
    } else if (rafRef.current) {
      cancelAnimationFrame(rafRef.current);
    }
    return () => rafRef.current && cancelAnimationFrame(rafRef.current);
  }, [playing, tick]);

  const reset = () => {
    setPlaying(false);
    setT(0);
    setAlertLog([]);
    lastStageRef.current = {};
    setGHistory(Array.from({ length: 30 }, (_, i) => ({ i, g: 0.3 })));
    if (pathRef.current) setPoint(pathRef.current.getPointAtLength(0));
  };

  const currentZone = getZoneAt(t);
  const currentG = gHistory[gHistory.length - 1].g;
  const threshold = currentZone ? currentZone.threshold : null;
  const stage = currentZone ? stageFor(currentG, currentZone.threshold) : "green";
  const speed = Math.round(150 - (currentZone ? currentZone.base * aggression * 35 : 0) + (Math.random() * 4 - 2));

  return (
    <div className="min-h-screen p-4 md:p-6" style={{ background: C.bg, color: C.text }}>
      <div className="max-w-5xl mx-auto space-y-4">
        <div>
          <p className="text-[11px] font-mono tracking-[0.25em] mb-1" style={{ color: C.blue }}>TRACKSIDE — SIMULATION MODE</p>
          <h1 className="text-lg font-semibold tracking-tight">Zone-Based Trajectory Alert — Software Simulation</h1>
        </div>

        <div className="flex items-start gap-2 rounded-lg p-3 text-xs font-mono" style={{ background: C.panel2, border: `1px solid ${C.line}`, color: C.muted }}>
          <Info size={14} className="mt-0.5 flex-shrink-0" />
          <p>This is a theoretical, software-only simulation. Track shape, zones, and lateral-g values are modeled in code — no physical GPS/IMU hardware is used. It demonstrates the zone-detection → threshold → alert logic that would run on real sensor data.</p>
        </div>

        <div className="grid grid-cols-12 gap-4">
          {/* track view */}
          <div className="col-span-12 md:col-span-7">
            <Panel title="Virtual Track" icon={Gauge}>
              <svg viewBox="0 0 480 300" className="w-full h-auto">
                <path ref={pathRef} d={TRACK_PATH} fill="none" stroke={C.line} strokeWidth="14" strokeLinecap="round" />
                {ZONES.map((z) => {
                  // approximate zone highlight by sampling path at range midpoints — simplified via stroke dasharray overlay omitted for brevity
                  return null;
                })}
                <path d={TRACK_PATH} fill="none" stroke={C.panel2} strokeWidth="10" strokeLinecap="round" />
                <circle cx={point.x} cy={point.y} r="7" fill={STAGE_META[stage].color} stroke={C.bg} strokeWidth="2">
                  <animate attributeName="opacity" values="1;0.6;1" dur="1s" repeatCount="indefinite" />
                </circle>
              </svg>
              <div className="flex flex-wrap gap-3 mt-2">
                {ZONES.map((z) => (
                  <span key={z.id} className="text-[11px] font-mono px-2 py-0.5 rounded" style={{ color: C.muted, border: `1px solid ${C.line}` }}>
                    {z.label} · threshold {z.threshold}g
                  </span>
                ))}
              </div>
            </Panel>
          </div>

          {/* controls + readout */}
          <div className="col-span-12 md:col-span-5 space-y-4">
            <Panel title="Controls">
              <div className="flex items-center gap-2 mb-4">
                <button
                  onClick={() => setPlaying((p) => !p)}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded text-sm"
                  style={{ background: C.blue, color: "#06121B" }}
                >
                  {playing ? <Pause size={14} /> : <Play size={14} />}
                  {playing ? "Pause" : "Run Lap"}
                </button>
                <button onClick={reset} className="flex items-center gap-1.5 px-3 py-1.5 rounded text-sm" style={{ border: `1px solid ${C.line}`, color: C.muted }}>
                  <RotateCcw size={14} /> Reset
                </button>
              </div>
              <label className="block text-[11px] font-mono mb-1" style={{ color: C.muted }}>
                DRIVING STYLE — aggression {aggression.toFixed(2)}x
              </label>
              <input
                type="range" min="0.7" max="1.5" step="0.01" value={aggression}
                onChange={(e) => setAggression(Number(e.target.value))}
                className="w-full mb-2"
              />
              <div className="flex gap-2">
                <button onClick={() => setAggression(0.85)} className="text-[11px] font-mono px-2 py-1 rounded" style={{ border: `1px solid ${C.green}55`, color: C.green }}>Clean Lap</button>
                <button onClick={() => setAggression(1.0)} className="text-[11px] font-mono px-2 py-1 rounded" style={{ border: `1px solid ${C.blue}55`, color: C.blue }}>Normal</button>
                <button onClick={() => setAggression(1.3)} className="text-[11px] font-mono px-2 py-1 rounded" style={{ border: `1px solid ${C.red}55`, color: C.red }}>Pushing Hard</button>
              </div>
            </Panel>

            <Panel title="Live Alert" icon={ShieldAlert} right={<span className="text-[11px] font-mono" style={{ color: STAGE_META[stage].color }}>{STAGE_META[stage].label}</span>}>
              <SignalStrip stage={stage} />
              <div className="grid grid-cols-3 gap-2 mt-3 text-center">
                <div>
                  <p className="text-lg font-mono">{currentZone ? currentZone.label : "Straight"}</p>
                  <p className="text-[10px] font-mono" style={{ color: C.faint }}>ZONE</p>
                </div>
                <div>
                  <p className="text-lg font-mono">{currentG.toFixed(2)}g</p>
                  <p className="text-[10px] font-mono" style={{ color: C.faint }}>LATERAL G</p>
                </div>
                <div>
                  <p className="text-lg font-mono">{speed}</p>
                  <p className="text-[10px] font-mono" style={{ color: C.faint }}>KM/H (SIM)</p>
                </div>
              </div>
              <div className="mt-3">
                <ResponsiveContainer width="100%" height={50}>
                  <LineChart data={gHistory}>
                    <Line type="monotone" dataKey="g" stroke={STAGE_META[stage].color} strokeWidth={2} dot={false} isAnimationActive={false} />
                    <YAxis hide domain={[0, 1.8]} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </Panel>
          </div>
        </div>

        <Panel title="Alert Log" icon={Radio}>
          {alertLog.length === 0 ? (
            <p className="text-xs font-mono" style={{ color: C.faint }}>No threshold exceedances yet — try "Pushing Hard" and run a lap.</p>
          ) : (
            <ul className="space-y-1">
              {alertLog.map((a, i) => (
                <li key={i} className="text-xs font-mono flex gap-2" style={{ color: C.muted }}>
                  <span style={{ color: C.faint }}>{a.time}</span>
                  <span style={{ color: C.red }}>{a.text}</span>
                </li>
              ))}
            </ul>
          )}
        </Panel>
      </div>
    </div>
  );
}
