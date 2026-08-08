import React, { useState, useEffect, useRef } from "react";
import { LineChart, Line, XAxis, YAxis, ResponsiveContainer } from "recharts";
import {
  Users, ShieldAlert, HeartPulse, Activity, Wind, Radio, Settings,
  LogOut, ChevronRight, CircleUser, Wifi, WifiOff, Construction,
  Video, Award, Trophy, TrendingUp, Target, Flag, Gauge,
} from "lucide-react";

// ---------------------------------------------------------------
// DESIGN TOKENS — dark telemetry palette, consistent across Trackside
// ---------------------------------------------------------------
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
  devYellow: "#E8C547",
};

const STAGE = {
  green: { label: "ON LINE", color: C.green },
  amber: { label: "APPROACHING LIMIT", color: C.amber },
  red: { label: "THRESHOLD EXCEEDED", color: C.red },
};

// ---------------------------------------------------------------
// SHARED UI PIECES
// ---------------------------------------------------------------
function SignalStrip({ stage = "green", size = "md" }) {
  const order = ["green", "green", "amber", "amber", "red"];
  const activeCount = stage === "green" ? 2 : stage === "amber" ? 4 : 5;
  const h = size === "sm" ? 8 : 12;
  return (
    <div className="flex items-center gap-1">
      {order.map((c, i) => {
        const lit = i < activeCount;
        return (
          <div key={i} style={{
            width: h * 1.6, height: h, borderRadius: 2,
            background: lit ? STAGE[c].color : C.line,
            boxShadow: lit ? `0 0 8px ${STAGE[c].color}88` : "none",
            transition: "all 200ms ease",
          }} />
        );
      })}
    </div>
  );
}

function Chip({ children, color }) {
  return (
    <span className="px-2 py-0.5 rounded text-xs font-mono tracking-wide"
      style={{ color, border: `1px solid ${color}55`, background: `${color}14` }}>
      {children}
    </span>
  );
}

function Panel({ title, icon: Icon, right, children, className = "" }) {
  return (
    <div className={`rounded-lg p-4 ${className}`} style={{ background: C.panel, border: `1px solid ${C.line}` }}>
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

// Yellow "development ongoing" banner used to wrap any Phase 1.5 / Phase 2 feature
function DevBanner({ phase, children }) {
  return (
    <div className="rounded-lg overflow-hidden" style={{ border: `1px solid ${C.devYellow}55` }}>
      <div className="flex items-center gap-2 px-3 py-1.5" style={{ background: `${C.devYellow}22` }}>
        <Construction size={13} style={{ color: C.devYellow }} />
        <span className="text-[11px] font-mono uppercase tracking-widest" style={{ color: C.devYellow }}>
          {phase} — Development Ongoing
        </span>
      </div>
      <div className="p-4" style={{ background: C.panel, opacity: 0.85 }}>
        {children}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------
// SIMULATED LIVE DATA (stand-in for the real IoT feed, Phase 1 core)
// ---------------------------------------------------------------
function useLiveSeries(min, max, points = 20) {
  const [data, setData] = useState(() => Array.from({ length: points }, (_, i) => ({ t: i, v: (min + max) / 2 })));
  const ref = useRef((min + max) / 2);
  useEffect(() => {
    const id = setInterval(() => {
      ref.current = Math.max(min, Math.min(max, ref.current + (Math.random() - 0.5) * (max - min) * 0.18));
      setData((d) => [...d.slice(1), { t: d[d.length - 1].t + 1, v: Math.round(ref.current) }]);
    }, 1400);
    return () => clearInterval(id);
  }, [min, max]);
  return data;
}

function MiniChart({ data, color }) {
  return (
    <ResponsiveContainer width="100%" height={50}>
      <LineChart data={data}>
        <Line type="monotone" dataKey="v" stroke={color} strokeWidth={2} dot={false} isAnimationActive={false} />
        <YAxis hide domain={["dataMin - 5", "dataMax + 5"]} />
        <XAxis hide dataKey="t" />
      </LineChart>
    </ResponsiveContainer>
  );
}

// ---------------------------------------------------------------
// LOGIN
// ---------------------------------------------------------------
function LoginScreen({ onLogin }) {
  const [role, setRole] = useState("coach");
  const [name, setName] = useState("");
  const roles = [
    { id: "coach", label: "Coach / Crew" },
    { id: "admin", label: "Admin" },
    { id: "driver", label: "Driver" },
  ];
  return (
    <div className="min-h-screen flex items-center justify-center px-4" style={{ background: C.bg }}>
      <div className="w-full max-w-sm">
        <div className="flex justify-center mb-6"><SignalStrip stage="amber" /></div>
        <div className="rounded-lg p-7" style={{ background: C.panel, border: `1px solid ${C.line}` }}>
          <div className="text-center mb-6">
            <p className="text-[11px] font-mono tracking-[0.25em] mb-1" style={{ color: C.blue }}>TRACKSIDE</p>
            <h1 className="text-lg font-semibold tracking-tight" style={{ color: C.text }}>Driver Safety & Performance Console</h1>
          </div>
          <div className="grid grid-cols-3 gap-2 mb-5">
            {roles.map((r) => (
              <button key={r.id} onClick={() => setRole(r.id)}
                className="py-2 rounded text-[11px] font-mono uppercase tracking-wide transition-colors"
                style={{
                  background: role === r.id ? C.blue : "transparent",
                  color: role === r.id ? "#06121B" : C.muted,
                  border: `1px solid ${role === r.id ? C.blue : C.line}`,
                }}>
                {r.label}
              </button>
            ))}
          </div>
          <label className="block text-[11px] font-mono mb-1" style={{ color: C.muted }}>NAME</label>
          <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Enter your name"
            className="w-full mb-4 px-3 py-2 rounded text-sm outline-none"
            style={{ background: C.panel2, border: `1px solid ${C.line}`, color: C.text }} />
          <label className="block text-[11px] font-mono mb-1" style={{ color: C.muted }}>ACCESS CODE</label>
          <input type="password" placeholder="••••••••"
            className="w-full mb-6 px-3 py-2 rounded text-sm outline-none"
            style={{ background: C.panel2, border: `1px solid ${C.line}`, color: C.text }} />
          <button onClick={() => onLogin(role, name || "Demo User")}
            className="w-full py-2.5 rounded text-sm font-medium flex items-center justify-center gap-2"
            style={{ background: C.blue, color: "#06121B" }}>
            Sign in <ChevronRight size={16} />
          </button>
          <p className="text-center text-[11px] font-mono mt-4" style={{ color: C.faint }}>
            intradomain access only — accounts are provisioned by the Admin
          </p>
        </div>
      </div>
    </div>
  );
}

function TopBar({ user, onLogout }) {
  return (
    <div className="border-b" style={{ borderColor: C.line, background: C.panel }}>
      <div className="max-w-6xl mx-auto px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <SignalStrip stage="green" size="sm" />
          <span className="text-xs font-mono tracking-widest" style={{ color: C.blue }}>TRACKSIDE</span>
        </div>
        <div className="flex items-center gap-3">
          <Settings size={15} style={{ color: C.faint }} />
          <span className="text-xs font-mono" style={{ color: C.muted }}>{user.name} · {user.role}</span>
          <button onClick={onLogout} className="flex items-center gap-1 text-xs font-mono" style={{ color: C.faint }}>
            <LogOut size={13} /> Sign out
          </button>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------
// COACH DASHBOARD — Phase 1 core live, Phase 2 analytics marked ongoing
// ---------------------------------------------------------------
const DRIVERS = [
  { id: 1, name: "A. Menon", kart: "#07" },
  { id: 2, name: "R. Iyer", kart: "#12" },
];

function CoachDashboard({ user, onLogout }) {
  const [activeId, setActiveId] = useState(1);
  const [threshold, setThreshold] = useState(1.15);
  const active = DRIVERS.find((d) => d.id === activeId);
  const speed = useLiveSeries(55, 145);
  const hr = useLiveSeries(138, 178);
  const spo2 = useLiveSeries(95, 99);
  const stage = speed[speed.length - 1].v > 120 ? "red" : speed[speed.length - 1].v > 95 ? "amber" : "green";

  return (
    <div className="min-h-screen" style={{ background: C.bg, color: C.text }}>
      <TopBar user={user} onLogout={onLogout} />
      <div className="max-w-6xl mx-auto px-4 py-5 grid grid-cols-12 gap-4">
        <div className="col-span-12 md:col-span-3 space-y-4">
          <Panel title="Driver Roster" icon={Users}>
            <div className="space-y-1">
              {DRIVERS.map((d) => (
                <button key={d.id} onClick={() => setActiveId(d.id)}
                  className="w-full text-left px-3 py-2 rounded flex items-center justify-between"
                  style={{ background: activeId === d.id ? C.panel2 : "transparent", border: `1px solid ${activeId === d.id ? C.blue + "55" : "transparent"}` }}>
                  <div>
                    <p className="text-sm">{d.name}</p>
                    <p className="text-[11px] font-mono" style={{ color: C.muted }}>Kart {d.kart}</p>
                  </div>
                  <CircleUser size={16} style={{ color: C.faint }} />
                </button>
              ))}
            </div>
          </Panel>
          <Panel title="Custom Threshold — Hairpin" icon={Target}>
            <p className="text-[11px] font-mono mb-2" style={{ color: C.muted }}>
              Set a training target for {active.name} (max {1.15}g, the calibrated safe limit)
            </p>
            <input type="range" min="0.6" max="1.15" step="0.01" value={threshold}
              onChange={(e) => setThreshold(Number(e.target.value))} className="w-full mb-1" />
            <p className="text-sm font-mono" style={{ color: C.blue }}>{threshold.toFixed(2)}g</p>
          </Panel>
        </div>

        <div className="col-span-12 md:col-span-9 space-y-4">
          <Panel title={`Live Trajectory — ${active.name}`} icon={ShieldAlert}
            right={<Chip color={STAGE[stage].color}>{STAGE[stage].label}</Chip>}>
            <div className="flex items-center justify-between">
              <SignalStrip stage={stage} />
              <div className="text-right">
                <p className="text-2xl font-mono font-semibold">{speed[speed.length - 1].v}</p>
                <p className="text-[11px] font-mono" style={{ color: C.muted }}>km/h</p>
              </div>
            </div>
            <div className="mt-3"><MiniChart data={speed} color={C.blue} /></div>
          </Panel>

          <div className="grid grid-cols-2 gap-4">
            <Panel title="Heart Rate" icon={HeartPulse}>
              <p className="text-xl font-mono">{hr[hr.length - 1].v} <span className="text-xs" style={{ color: C.muted }}>bpm</span></p>
              <MiniChart data={hr} color={C.red} />
            </Panel>
            <Panel title="Blood Oxygen" icon={Activity}>
              <p className="text-xl font-mono">{spo2[spo2.length - 1].v}<span className="text-xs" style={{ color: C.muted }}>%</span></p>
              <MiniChart data={spo2} color={C.green} />
            </Panel>
          </div>

          <DevBanner phase="Phase 2">
            <div className="flex items-center gap-2 mb-2">
              <TrendingUp size={14} style={{ color: C.muted }} />
              <p className="text-xs font-mono uppercase tracking-widest" style={{ color: C.muted }}>Cross-Driver Trend Analytics</p>
            </div>
            <p className="text-sm" style={{ color: C.faint }}>
              Mock preview — corner-difficulty ranking across all drivers, recurring-risk flagging, and consistency-based comparison will appear here once the ML/analytics layer is built.
            </p>
          </DevBanner>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------
// ADMIN DASHBOARD — Phase 1 core, no Phase 2 content needed here
// ---------------------------------------------------------------
const MOCK_USERS = [
  { id: 1, name: "Coach Nair", role: "Coach", status: "Active" },
  { id: 2, name: "A. Menon", role: "Driver", status: "Active" },
  { id: 3, name: "R. Iyer", role: "Driver", status: "Active" },
];

function AdminDashboard({ user, onLogout }) {
  return (
    <div className="min-h-screen" style={{ background: C.bg, color: C.text }}>
      <TopBar user={user} onLogout={onLogout} />
      <div className="max-w-6xl mx-auto px-4 py-5 space-y-4">
        <div className="grid grid-cols-3 gap-4">
          <Panel title="Glove Unit" icon={Wifi}>
            <div className="flex items-center gap-2"><span style={{ color: C.green }}>●</span><p className="text-sm">Connected</p></div>
          </Panel>
          <Panel title="Kart Unit" icon={Wifi}>
            <div className="flex items-center gap-2"><span style={{ color: C.green }}>●</span><p className="text-sm">Connected · GPS lock</p></div>
          </Panel>
          <Panel title="Biometric Strap" icon={WifiOff}>
            <div className="flex items-center gap-2"><span style={{ color: C.amber }}>●</span><p className="text-sm">Pairing…</p></div>
          </Panel>
        </div>
        <Panel title="User Management" icon={Users}>
          <table className="w-full text-sm">
            <thead>
              <tr style={{ color: C.muted }} className="text-[11px] font-mono uppercase text-left">
                <th className="pb-2">Name</th><th className="pb-2">Role</th><th className="pb-2">Status</th><th className="pb-2 text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {MOCK_USERS.map((u) => (
                <tr key={u.id} style={{ borderTop: `1px solid ${C.line}` }}>
                  <td className="py-2">{u.name}</td>
                  <td className="py-2" style={{ color: C.muted }}>{u.role}</td>
                  <td className="py-2"><Chip color={C.green}>{u.status}</Chip></td>
                  <td className="py-2 text-right">
                    <button className="text-xs font-mono px-2 py-1 rounded" style={{ color: C.blue, border: `1px solid ${C.blue}44` }}>Edit</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Panel>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------
// DRIVER DASHBOARD — Phase 1 core raw data + Phase 1.5/2 features marked ongoing
// ---------------------------------------------------------------
function DriverDashboard({ user, onLogout }) {
  const zones = [
    { name: "Hairpin", count: 6 },
    { name: "Sweeper", count: 0 },
    { name: "Chicane", count: 2 },
  ];
  return (
    <div className="min-h-screen" style={{ background: C.bg, color: C.text }}>
      <TopBar user={user} onLogout={onLogout} />
      <div className="max-w-6xl mx-auto px-4 py-5 space-y-4">
        <Panel title="Session Setup" icon={Flag}>
          <div className="flex gap-2">
            <button className="text-xs font-mono px-3 py-1.5 rounded" style={{ background: C.blue, color: "#06121B" }}>Safety Mode</button>
            <button className="text-xs font-mono px-3 py-1.5 rounded" style={{ border: `1px solid ${C.line}`, color: C.muted }}>Performance Mode</button>
          </div>
        </Panel>

        <Panel title="Zone-by-Zone Breakdown (last 5 sessions)" icon={Gauge}>
          <div className="grid grid-cols-3 gap-3">
            {zones.map((z) => (
              <div key={z.name} className="rounded p-3 text-center" style={{ background: C.panel2, border: `1px solid ${C.line}` }}>
                <p className="text-2xl font-mono" style={{ color: z.count > 3 ? C.red : z.count > 0 ? C.amber : C.green }}>{z.count}</p>
                <p className="text-[11px] font-mono" style={{ color: C.muted }}>{z.name} alerts</p>
              </div>
            ))}
          </div>
        </Panel>

        <div className="grid grid-cols-2 gap-4">
          <Panel title="Best Lap (raw)" icon={Trophy}>
            <p className="text-sm" style={{ color: C.muted }}>Lap 6 — cleanest of the session, no threshold-exceeded alerts in any zone.</p>
          </Panel>
          <Panel title="Session Goal" icon={Target}>
            <p className="text-sm" style={{ color: C.muted }}>Zero red alerts at the Hairpin — <span style={{ color: C.red }}>not met</span> (2 red alerts today).</p>
          </Panel>
        </div>

        <DevBanner phase="Phase 1.5">
          <div className="flex items-center gap-2 mb-2">
            <Video size={14} style={{ color: C.muted }} />
            <p className="text-xs font-mono uppercase tracking-widest" style={{ color: C.muted }}>Alert Clips</p>
          </div>
          <p className="text-sm mb-2" style={{ color: C.faint }}>
            Mock preview — a short rolling-buffer video clip will play here for each alert, synced to its timestamp.
          </p>
          <div className="w-full h-24 rounded flex items-center justify-center text-xs font-mono" style={{ background: C.bg, color: C.faint, border: `1px dashed ${C.line}` }}>
            ▶ clip placeholder — Hairpin, Lap 4
          </div>
        </DevBanner>

        <DevBanner phase="Phase 2">
          <div className="flex items-center gap-2 mb-2">
            <Award size={14} style={{ color: C.muted }} />
            <p className="text-xs font-mono uppercase tracking-widest" style={{ color: C.muted }}>Guidance, Trends & Badges</p>
          </div>
          <p className="text-sm" style={{ color: C.faint }}>
            Mock preview — plain-language coaching tips, the personal trend graph, the Career/Longevity graph (unlocks after 5 sessions), driving-style badges, and opt-in leaderboard will appear here once the analysis layer is built.
          </p>
        </DevBanner>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------
// APP ROOT
// ---------------------------------------------------------------
export default function TracksideApp() {
  const [user, setUser] = useState(null);
  if (!user) return <LoginScreen onLogin={(role, name) => setUser({ role, name })} />;
  if (user.role === "coach") return <CoachDashboard user={user} onLogout={() => setUser(null)} />;
  if (user.role === "admin") return <AdminDashboard user={user} onLogout={() => setUser(null)} />;
  return <DriverDashboard user={user} onLogout={() => setUser(null)} />;
}
