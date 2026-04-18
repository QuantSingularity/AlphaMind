import type React from "react";
import { useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  RadarChart,
  Radar,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { formatCurrency } from "../utils/format";

const STRESS_SCENARIOS = [
  {
    name: "2020 COVID Crash",
    pnl: -18420,
    duration: "33 days",
    recovery: "5 months",
  },
  {
    name: "2022 Rate Shock",
    pnl: -12810,
    duration: "180 days",
    recovery: "14 months",
  },
  {
    name: "2008 GFC",
    pnl: -44200,
    duration: "512 days",
    recovery: "4.5 years",
  },
  {
    name: "2000 Dot-com",
    pnl: -31900,
    duration: "929 days",
    recovery: "7 years",
  },
  {
    name: "1987 Black Monday",
    pnl: -9870,
    duration: "1 day",
    recovery: "2 years",
  },
  {
    name: "+3σ Vol Spike",
    pnl: -7240,
    duration: "5 days",
    recovery: "3 weeks",
  },
];

const CORRELATION_MATRIX = [
  { asset: "AAPL", AAPL: 1.0, MSFT: 0.82, GOOGL: 0.76, TSLA: 0.58, JPM: 0.41 },
  { asset: "MSFT", AAPL: 0.82, MSFT: 1.0, GOOGL: 0.79, TSLA: 0.52, JPM: 0.45 },
  { asset: "GOOGL", AAPL: 0.76, MSFT: 0.79, GOOGL: 1.0, TSLA: 0.49, JPM: 0.39 },
  { asset: "TSLA", AAPL: 0.58, MSFT: 0.52, GOOGL: 0.49, TSLA: 1.0, JPM: 0.28 },
  { asset: "JPM", AAPL: 0.41, MSFT: 0.45, GOOGL: 0.39, TSLA: 0.28, JPM: 1.0 },
];

const RISK_RADAR = [
  { metric: "Market Risk", value: 72 },
  { metric: "Liquidity Risk", value: 31 },
  { metric: "Concentration", value: 58 },
  { metric: "Leverage", value: 20 },
  { metric: "Tail Risk", value: 44 },
  { metric: "Counterparty", value: 15 },
];

function generateVaRDistribution(): {
  return: string;
  frequency: number;
  tail: boolean;
}[] {
  const bins: { return: string; frequency: number; tail: boolean }[] = [];
  for (let r = -5.0; r <= 5.0; r += 0.5) {
    const z = r / 1.4;
    const freq = Math.round(Math.exp(-0.5 * z * z) * 80 + Math.random() * 10);
    bins.push({ return: r.toFixed(1), frequency: freq, tail: r <= -2.0 });
  }
  return bins;
}

type TabId = "overview" | "stress" | "correlation" | "var";

export const RiskManagement: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabId>("overview");
  const varDist = useMemo(() => generateVaRDistribution(), []);

  const tabs: { id: TabId; label: string }[] = [
    { id: "overview", label: "Risk Overview" },
    { id: "stress", label: "Stress Testing" },
    { id: "correlation", label: "Correlation" },
    { id: "var", label: "VaR / CVaR" },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Risk Management</h1>
        <p className="mt-1 text-sm text-gray-500">
          Bayesian VaR, stress testing, and correlation analytics
        </p>
      </div>

      {/* Top-line risk KPIs */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
        {[
          {
            label: "Portfolio VaR 95%",
            value: "$4,820",
            sub: "1-day parametric",
            color: "text-orange-600",
          },
          {
            label: "CVaR 95%",
            value: "$6,740",
            sub: "expected shortfall",
            color: "text-red-600",
          },
          {
            label: "Stress P&L (worst)",
            value: "-$44,200",
            sub: "GFC scenario",
            color: "text-red-700",
          },
          {
            label: "Portfolio Beta",
            value: "1.09",
            sub: "vs S&P 500",
            color: "text-gray-900",
          },
          {
            label: "Volatility (Ann.)",
            value: "14.2%",
            sub: "realised 90d",
            color: "text-gray-900",
          },
          {
            label: "Risk Utilisation",
            value: "68%",
            sub: "of risk budget",
            color: "text-yellow-600",
          },
        ].map((m) => (
          <div key={m.label} className="bg-white shadow rounded-lg p-4">
            <p className="text-xs text-gray-500">{m.label}</p>
            <p className={`text-lg font-bold ${m.color}`}>{m.value}</p>
            <p className="text-xs text-gray-400 mt-0.5">{m.sub}</p>
          </div>
        ))}
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <nav className="-mb-px flex space-x-6">
          {tabs.map((t) => (
            <button
              key={t.id}
              onClick={() => setActiveTab(t.id)}
              className={`py-3 text-sm font-medium border-b-2 transition-colors ${activeTab === t.id ? "border-blue-600 text-blue-600" : "border-transparent text-gray-500 hover:text-gray-700"}`}
            >
              {t.label}
            </button>
          ))}
        </nav>
      </div>

      {activeTab === "overview" && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="bg-white shadow rounded-lg p-6">
            <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide mb-4">
              Risk Spider Chart
            </h2>
            <ResponsiveContainer width="100%" height={280}>
              <RadarChart data={RISK_RADAR}>
                <PolarGrid />
                <PolarAngleAxis dataKey="metric" tick={{ fontSize: 11 }} />
                <PolarRadiusAxis angle={90} domain={[0, 100]} tick={false} />
                <Radar
                  name="Risk Score"
                  dataKey="value"
                  stroke="#2563eb"
                  fill="#2563eb"
                  fillOpacity={0.25}
                />
                <Tooltip formatter={(v) => [`${v}/100`, "Risk Score"]} />
              </RadarChart>
            </ResponsiveContainer>
          </div>
          <div className="bg-white shadow rounded-lg p-6">
            <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide mb-4">
              Risk Budget Utilisation
            </h2>
            <div className="space-y-3">
              {[
                { name: "Market Risk", used: 72, limit: 100, color: "#2563eb" },
                {
                  name: "Sector Concentration",
                  used: 58,
                  limit: 70,
                  color: "#f59e0b",
                },
                {
                  name: "Single-Name Limit",
                  used: 28,
                  limit: 30,
                  color: "#10b981",
                },
                { name: "Leverage", used: 20, limit: 100, color: "#8b5cf6" },
                {
                  name: "Liquidity Risk",
                  used: 31,
                  limit: 80,
                  color: "#06b6d4",
                },
              ].map((b) => (
                <div key={b.name}>
                  <div className="flex justify-between text-xs text-gray-500 mb-1">
                    <span>{b.name}</span>
                    <span
                      className={
                        b.used / b.limit > 0.85
                          ? "text-red-600 font-semibold"
                          : ""
                      }
                    >
                      {b.used}/{b.limit}
                    </span>
                  </div>
                  <div className="w-full h-3 bg-gray-100 rounded-full overflow-hidden">
                    <div
                      className="h-full rounded-full transition-all"
                      style={{
                        width: `${(b.used / b.limit) * 100}%`,
                        background:
                          b.used / b.limit > 0.85 ? "#ef4444" : b.color,
                      }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {activeTab === "stress" && (
        <div className="space-y-6">
          <div className="bg-white shadow rounded-lg overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-200">
              <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide">
                Historical Stress Scenarios
              </h2>
            </div>
            <table className="min-w-full text-sm divide-y divide-gray-100">
              <thead className="bg-gray-50">
                <tr>
                  {[
                    "Scenario",
                    "Estimated P&L",
                    "Duration",
                    "Recovery",
                    "Status",
                  ].map((h) => (
                    <th
                      key={h}
                      className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase"
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-100">
                {STRESS_SCENARIOS.map((s) => (
                  <tr key={s.name} className="hover:bg-gray-50">
                    <td className="px-6 py-4 font-medium text-gray-900">
                      {s.name}
                    </td>
                    <td
                      className={`px-6 py-4 font-semibold ${s.pnl < -20000 ? "text-red-700" : "text-red-500"}`}
                    >
                      {formatCurrency(s.pnl)}
                    </td>
                    <td className="px-6 py-4 text-gray-500">{s.duration}</td>
                    <td className="px-6 py-4 text-gray-500">{s.recovery}</td>
                    <td className="px-6 py-4">
                      <span
                        className={`px-2 py-0.5 rounded-full text-xs font-medium ${s.pnl > -15000 ? "bg-yellow-100 text-yellow-700" : "bg-red-100 text-red-700"}`}
                      >
                        {s.pnl > -15000 ? "Manageable" : "Severe"}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="bg-white shadow rounded-lg p-6">
            <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide mb-4">
              P&L Sensitivity to Stress
            </h2>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={STRESS_SCENARIOS} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                <XAxis
                  type="number"
                  tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`}
                  tick={{ fontSize: 11 }}
                />
                <YAxis
                  type="category"
                  dataKey="name"
                  width={140}
                  tick={{ fontSize: 10 }}
                />
                <Tooltip
                  formatter={(v) => [
                    formatCurrency(Number(v)),
                    "Estimated P&L",
                  ]}
                />
                <Bar dataKey="pnl" fill="#ef4444" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {activeTab === "correlation" && (
        <div className="bg-white shadow rounded-lg p-6">
          <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide mb-4">
            Pairwise Asset Correlations (90-day)
          </h2>
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead>
                <tr>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500"></th>
                  {["AAPL", "MSFT", "GOOGL", "TSLA", "JPM"].map((t) => (
                    <th
                      key={t}
                      className="px-4 py-2 text-center text-xs font-medium text-gray-700"
                    >
                      {t}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {CORRELATION_MATRIX.map((row) => (
                  <tr key={row.asset}>
                    <td className="px-4 py-3 font-semibold text-gray-700">
                      {row.asset}
                    </td>
                    {(["AAPL", "MSFT", "GOOGL", "TSLA", "JPM"] as const).map(
                      (t) => {
                        const val = row[t];
                        const opacity = Math.abs(val);
                        const bg =
                          val >= 1
                            ? "bg-gray-100"
                            : val > 0.7
                              ? `rgba(239,68,68,${opacity})`
                              : val > 0.4
                                ? `rgba(251,191,36,${opacity})`
                                : `rgba(16,185,129,${opacity * 0.5})`;
                        return (
                          <td
                            key={t}
                            className="px-4 py-3 text-center text-sm font-medium"
                            style={{ background: bg }}
                          >
                            {val.toFixed(2)}
                          </td>
                        );
                      },
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="text-xs text-gray-400 mt-3">
            🔴 High correlation (&gt;0.7) increases systemic risk.
            Diversification benefit is highest among low-correlation pairs.
          </p>
        </div>
      )}

      {activeTab === "var" && (
        <div className="space-y-6">
          <div className="bg-white shadow rounded-lg p-6">
            <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide mb-1">
              Return Distribution & VaR Thresholds
            </h2>
            <p className="text-xs text-gray-400 mb-4">
              Red bars = tail losses beyond 95% VaR threshold
            </p>
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={varDist}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis
                  dataKey="return"
                  tick={{ fontSize: 10 }}
                  label={{
                    value: "Daily Return (%)",
                    position: "insideBottom",
                    offset: -2,
                    fontSize: 11,
                  }}
                />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip
                  formatter={(v, _n, p) => [v, `Return: ${p.payload.return}%`]}
                />
                <Bar dataKey="frequency" radius={[2, 2, 0, 0]}>
                  {varDist.map((entry, i) => (
                    <Cell key={i} fill={entry.tail ? "#ef4444" : "#2563eb"} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            {[
              {
                label: "VaR 95% (1d)",
                value: "$4,820",
                method: "Parametric Normal",
                note: "3.85% of portfolio",
              },
              {
                label: "VaR 99% (1d)",
                value: "$7,140",
                method: "Historical Simulation",
                note: "5.70% of portfolio",
              },
              {
                label: "CVaR 95% (1d)",
                value: "$6,740",
                method: "Expected Shortfall",
                note: "Avg of worst 5% scenarios",
              },
            ].map((v) => (
              <div key={v.label} className="bg-white shadow rounded-lg p-5">
                <p className="text-xs text-gray-500 font-medium">{v.label}</p>
                <p className="text-2xl font-bold text-red-600">{v.value}</p>
                <p className="text-xs text-gray-400 mt-1">{v.method}</p>
                <p className="text-xs text-gray-500 mt-0.5">{v.note}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
