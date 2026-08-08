import React, { useState, useEffect, useRef } from "react";
import {
  LineChart, Line, XAxis, YAxis, ResponsiveContainer, Tooltip,
} from "recharts";
import {
  Gauge, Activity, HeartPulse, Wind, Users, ShieldAlert,
  LogOut, Radio, Settings, ChevronRight, CircleUser, Wifi, WifiOff,
} from "lucide-react";

// ---------- design tokens ----------
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

const STAGE = {
  green: { label: "ON LINE", color: C.green },
  amber: { label: "APPROACHING LIMIT", color: C.amber },
  red: { label: "TRAJECTORY RISK", color: C.red },
};

// ---------- signature element: 5-segment signal strip (mirrors the glove LEDs) ----------
function SignalStrip({ stage = "green", size = "md" }) {
  const order = ["green", "green", "amber", "amber", "red"];
  const activeCount = stage === "green" ? 2 : stage === "amber" ? 4 : 5;
  const h = size === "sm" ? 8 : 12;
  return (
    <div className="flex items-center gap-1">
      {order.map((c, i) => {
        const lit = i < activeCount;
        return (
          <div
            key={i}
            style={{
              width: h * 1.6,
              height: h,
              borderRadius: 2,
              background: lit ? STAGE[c].color : C.line,
              boxShadow: lit ? `0 0 8px ${STAGE[c].color}88` : "none",
              transition: "all 200ms ease",
            }}
          />
        );
      })}
    </div>
  );
}

function Chip({ children, color }) {
  return (
    <span
      className="px-2 py-0.5 rounded text-xs font-mono tracking-wide"
      style={{ color, border: `1px solid ${color}55`, background: `${color}14` }}
    >
      {children}
    </span>
  );
}

function Panel({ title, icon: Icon, right, children, className = "" }) {
  return (
    <div
      className={`rounded-lg p-4 ${className}`}
      style={{ background: C.panel, border: `1px solid ${C.line}` }}
    >
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          {Icon && <Icon size={15} style={{ color: C.muted }} />}
          <h3 className="text-xs font-mono uppercase tracking-widest" style={{ color: C.muted }}>
            {title}
          </h3>
        </div>
        {right}
      </div>
      {children}
    </div>
  );
}

// ---------- simulated live data ----------
function useLiveSeries(seed, min, max, points = 24) {
  const [data, setData] = useState(() =>
    Array.from({ length: points }, (_, i) => ({ t: i, v: (min + max) / 2 }))
  );
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
    <ResponsiveContainer width="100%" height={54}>
      <LineChart data={data}>
        <Line type="monotone" dataKey="v" stroke={color} strokeWidth={2} dot={false} isAnimationActive={false} />
        <YAxis hide domain={["dataMin - 5", "dataMax + 5"]} />
        <XAxis hide dataKey="t" />
      </LineChart>
    </ResponsiveContainer>
  );
}

// ---------- driver roster (mock) ----------
const DRIVERS = [
  { id: 1, name: "A. Menon", kart: "#07", session: "Free Practice" },
  { id: 2, name: "R. Iyer", kart: "#12", session: "Free Practice" },
  { id: 3, name: "S. Thomas", kart: "#03", session: "Timed Run" },
];

const STAGES = ["green", "green", "green", "amber", "green", "red", "amber", "green"];

// ---------- Login ----------
function LoginScreen({ onLogin }) {
  const [role, setRole] = useState("coach");
  const [name, setName] = useState("");

  return (
    <div className="min-h-screen flex items-center justify-center px-4" style={{ background: C.bg }}>
      <div className="w-full max-w-sm">
        <div className="flex justify-center mb-6">
          <SignalStrip stage="amber" />
        </div>
        <div className="rounded-lg p-7" style={{ background: C.panel, border: `1px solid ${C.line}` }}>
          <div className="text-center mb-6">
            <p className="text-[11px] font-mono tracking-[0.25em] mb-1" style={{ color: C.blue }}>
              TRACKSIDE
            </p>
            <h1 className="text-lg font-semibold tracking-tight" style={{ color: C.text }}>
              Driver Safety & Performance Console
            </h1>
          </div>

          <div className="grid grid-cols-2 gap-2 mb-5">
            {["coach", "admin"].map((r) => (
              <button
                key={r}
                onClick={() => setRole(r)}
                className="py-2 rounded text-xs font-mono uppercase tracking-widest transition-colors"
                style={{
                  background: role === r ? C.blue : "transparent",
                  color: role === r ? "#06121B" : C.muted,
                  border: `1px solid ${role === r ? C.blue : C.line}`,
                }}
              >
                {r === "coach" ? "Coach / Crew" : "Admin"}
              </button>
            ))}
          </div>

          <label className="block text-[11px] font-mono mb-1" style={{ color: C.muted }}>
            NAME
          </label>
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder={role === "coach" ? "e.g. Coach Nair" : "e.g. Admin"}
            className="w-full mb-4 px-3 py-2 rounded text-sm outline-none"
            style={{ background: C.panel2, border: `1px solid ${C.line}`, color: C.text }}
          />
          <label className="block text-[11px] font-mono mb-1" style={{ color: C.muted }}>
            ACCESS CODE
          </label>
          <input
            type="password"
            placeholder="••••••••"
            className="w-full mb-6 px-3 py-2 rounded text-sm outline-none"
            style={{ background: C.panel2, border: `1px solid ${C.line}`, color: C.text }}
          />

          <button
            onClick={() => onLogin(role, name || (role === "coach" ? "Coach Nair" : "Admin"))}
            className="w-full py-2.5 rounded text-sm font-medium flex items-center justify-center gap-2"
            style={{ background: C.blue, color: "#06121B" }}
          >
            Sign in <ChevronRight size={16} />
          </button>
          <p className="text-center text-[11px] font-mono mt-4" style={{ color: C.faint }}>
            demo prototype — auth is simulated, no backend attached
          </p>
        </div>
      </div>
    </div>
  );
}

// ---------- Coach Dashboard ----------
function CoachDashboard({ user, onLogout }) {
  const [activeId, setActiveId] = useState(1);
  const [stageIdx, setStageIdx] = useState(0);
  const active = DRIVERS.find((d) => d.id === activeId);

  const speed = useLiveSeries("speed", 55, 145);
  const hr = useLiveSeries("hr", 138, 178);
  const spo2 = useLiveSeries("spo2", 95, 99);
  const breath = useLiveSeries("breath", 18, 34);

  useEffect(() => {
    const id = setInterval(() => setStageIdx((i) => (i + 1) % STAGES.length), 2600);
    return () => clearInterval(id);
  }, []);
  const stage = STAGES[stageIdx];
  const stress = hr[hr.length - 1].v > 165 ? "High" : hr[hr.length - 1].v > 150 ? "Mid" : "Low";
  const stressColor = stress === "High" ? C.red : stress === "Mid" ? C.amber : C.green;

  return (
    <div className="min-h-screen" style={{ background: C.bg, color: C.text }}>
      <TopBar user={user} onLogout={onLogout} />
      <div className="max-w-6xl mx-auto px-4 py-5 grid grid-cols-12 gap-4">
        {/* driver list */}
        <div className="col-span-12 md:col-span-3">
          <Panel title="Session Roster" icon={Users}>
            <div className="space-y-1">
              {DRIVERS.map((d) => (
                <button
                  key={d.id}
                  onClick={() => setActiveId(d.id)}
                  className="w-full text-left px-3 py-2 rounded flex items-center justify-between"
                  style={{
                    background: activeId === d.id ? C.panel2 : "transparent",
                    border: `1px solid ${activeId === d.id ? C.blue + "55" : "transparent"}`,
                  }}
                >
                  <div>
                    <p className="text-sm">{d.name}</p>
                    <p className="text-[11px] font-mono" style={{ color: C.muted }}>
                      Kart {d.kart} · {d.session}
                    </p>
                  </div>
                  <CircleUser size={16} style={{ color: C.faint }} />
                </button>
              ))}
            </div>
          </Panel>
        </div>

        {/* main */}
        <div className="col-span-12 md:col-span-9 space-y-4">
          <Panel
            title={`Live Trajectory — ${active.name}`}
            icon={ShieldAlert}
            right={<Chip color={STAGE[stage].color}>{STAGE[stage].label}</Chip>}
          >
            <div className="flex items-center justify-between">
              <SignalStrip stage={stage} />
              <div className="text-right">
                <p className="text-2xl font-mono font-semibold">{speed[speed.length - 1].v}</p>
                <p className="text-[11px] font-mono" style={{ color: C.muted }}>km/h · corner reference model</p>
              </div>
            </div>
            <div className="mt-3">
              <MiniChart data={speed} color={C.blue} />
            </div>
          </Panel>

          <div className="grid grid-cols-3 gap-4">
            <Panel title="Heart Rate" icon={HeartPulse}>
              <p className="text-xl font-mono">{hr[hr.length - 1].v} <span className="text-xs" style={{ color: C.muted }}>bpm</span></p>
              <MiniChart data={hr} color={C.red} />
            </Panel>
            <Panel title="Blood Oxygen" icon={Activity}>
              <p className="text-xl font-mono">{spo2[spo2.length - 1].v}<span className="text-xs" style={{ color: C.muted }}>%</span></p>
              <MiniChart data={spo2} color={C.green} />
            </Panel>
            <Panel title="Breathing Rate" icon={Wind}>
              <p className="text-xl font-mono">{breath[breath.length - 1].v} <span className="text-xs" style={{ color: C.muted }}>br/min</span></p>
              <MiniChart data={breath} color={C.blue} />
            </Panel>
          </div>

          <Panel title="Driver Condition" icon={Radio} right={<Chip color={stressColor}>{stress} STRESS</Chip>}>
            <p className="text-sm" style={{ color: C.muted }}>
              Composite of heart rate, SpO₂ and breathing rate against {active.name}'s session baseline. Use this alongside the trajectory stage above to decide on pace, pit, or rest calls.
            </p>
          </Panel>
        </div>
      </div>
    </div>
  );
}

// ---------- Admin Dashboard ----------
const MOCK_USERS = [
  { id: 1, name: "Coach Nair", role: "Coach", status: "Active" },
  { id: 2, name: "A. Menon", role: "Driver", status: "Active" },
  { id: 3, name: "R. Iyer", role: "Driver", status: "Active" },
  { id: 4, name: "S. Thomas", role: "Driver", status: "Inactive" },
];

function AdminDashboard({ user, onLogout }) {
  return (
    <div className="min-h-screen" style={{ background: C.bg, color: C.text }}>
      <TopBar user={user} onLogout={onLogout} />
      <div className="max-w-6xl mx-auto px-4 py-5 space-y-4">
        <div className="grid grid-cols-3 gap-4">
          <Panel title="Glove Unit" icon={Wifi}>
            <div className="flex items-center gap-2">
              <span style={{ color: C.green }}>●</span>
              <p className="text-sm">Connected · ESP-NOW</p>
            </div>
          </Panel>
          <Panel title="Track Unit" icon={Wifi}>
            <div className="flex items-center gap-2">
              <span style={{ color: C.green }}>●</span>
              <p className="text-sm">Connected · GPS lock</p>
            </div>
          </Panel>
          <Panel title="Biometric Strap" icon={WifiOff}>
            <div className="flex items-center gap-2">
              <span style={{ color: C.amber }}>●</span>
              <p className="text-sm">Pairing…</p>
            </div>
          </Panel>
        </div>

        <Panel title="User Management" icon={Users}>
          <table className="w-full text-sm">
            <thead>
              <tr style={{ color: C.muted }} className="text-[11px] font-mono uppercase text-left">
                <th className="pb-2">Name</th>
                <th className="pb-2">Role</th>
                <th className="pb-2">Status</th>
                <th className="pb-2 text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {MOCK_USERS.map((u) => (
                <tr key={u.id} style={{ borderTop: `1px solid ${C.line}` }}>
                  <td className="py-2">{u.name}</td>
                  <td className="py-2" style={{ color: C.muted }}>{u.role}</td>
                  <td className="py-2">
                    <Chip color={u.status === "Active" ? C.green : C.faint}>{u.status}</Chip>
                  </td>
                  <td className="py-2 text-right">
                    <button className="text-xs font-mono px-2 py-1 rounded" style={{ color: C.blue, border: `1px solid ${C.blue}44` }}>
                      Edit
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Panel>

        <Panel title="Session Analytics" icon={Settings}>
          <p className="text-sm" style={{ color: C.muted }}>
            3 active drivers · 2 sessions logged today · 0 unresolved connectivity issues.
          </p>
        </Panel>
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
          <span className="text-xs font-mono" style={{ color: C.muted }}>
            {user.name} · {user.role === "coach" ? "Coach" : "Admin"}
          </span>
          <button onClick={onLogout} className="flex items-center gap-1 text-xs font-mono" style={{ color: C.faint }}>
            <LogOut size={13} /> Sign out
          </button>
        </div>
      </div>
    </div>
  );
}

export default function KartingSystem() {
  const [user, setUser] = useState(null);
  if (!user) return <LoginScreen onLogin={(role, name) => setUser({ role, name })} />;
  return user.role === "coach" ? (
    <CoachDashboard user={user} onLogout={() => setUser(null)} />
  ) : (
    <AdminDashboard user={user} onLogout={() => setUser(null)} />
  );
}
