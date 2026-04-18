import type React from "react";
import { useMemo, useState } from "react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { PieLabelRenderProps } from "recharts";
import { usePositions } from "../hooks/usePortfolio";
import {
  formatCurrency,
  formatPercentage,
  getColorForValue,
} from "../utils/format";

const COLORS = [
  "#2563eb",
  "#10b981",
  "#f59e0b",
  "#ef4444",
  "#8b5cf6",
  "#06b6d4",
];

interface Position {
  id: string;
  ticker: string;
  sector: string;
  quantity: number;
  entryPrice: number;
  currentPrice: number;
  unrealizedPnL: number;
  weight: number;
  beta: number;
  sharpeContrib: number;
  var95: number;
}

const mockPositions: Position[] = [
  {
    id: "1",
    ticker: "AAPL",
    sector: "Technology",
    quantity: 100,
    entryPrice: 150.0,
    currentPrice: 175.5,
    unrealizedPnL: 2550.0,
    weight: 0.28,
    beta: 1.21,
    sharpeContrib: 0.42,
    var95: 1240,
  },
  {
    id: "2",
    ticker: "MSFT",
    sector: "Technology",
    quantity: 50,
    entryPrice: 300.0,
    currentPrice: 338.0,
    unrealizedPnL: 1900.0,
    weight: 0.27,
    beta: 0.92,
    sharpeContrib: 0.38,
    var95: 980,
  },
  {
    id: "3",
    ticker: "GOOGL",
    sector: "Communication",
    quantity: 25,
    entryPrice: 2800.0,
    currentPrice: 2950.0,
    unrealizedPnL: 3750.0,
    weight: 0.19,
    beta: 1.05,
    sharpeContrib: 0.29,
    var95: 1560,
  },
  {
    id: "4",
    ticker: "TSLA",
    sector: "Consumer Disc.",
    quantity: 30,
    entryPrice: 700.0,
    currentPrice: 742.0,
    unrealizedPnL: 1260.0,
    weight: 0.11,
    beta: 1.89,
    sharpeContrib: 0.14,
    var95: 2100,
  },
  {
    id: "5",
    ticker: "JPM",
    sector: "Financials",
    quantity: 80,
    entryPrice: 145.0,
    currentPrice: 158.0,
    unrealizedPnL: 1040.0,
    weight: 0.1,
    beta: 1.12,
    sharpeContrib: 0.18,
    var95: 720,
  },
  {
    id: "6",
    ticker: "BRK.B",
    sector: "Financials",
    quantity: 40,
    entryPrice: 320.0,
    currentPrice: 331.0,
    unrealizedPnL: 440.0,
    weight: 0.05,
    beta: 0.78,
    sharpeContrib: 0.09,
    var95: 380,
  },
];

const riskMetrics = {
  portfolioVar95: 4820,
  portfolioCVaR95: 6740,
  portfolioBeta: 1.09,
  portfolioSharpe: 2.31,
  portfolioSortino: 3.14,
  maxDrawdown: 0.089,
  informationRatio: 0.74,
  trackingError: 0.032,
  calmarRatio: 2.87,
  volatility: 0.142,
};

function generateDrawdownData(): { date: string; drawdown: number }[] {
  const data = [];
  let peak = 100000;
  let equity = 100000;
  const startDate = new Date("2024-01-01");
  for (let i = 0; i < 90; i++) {
    equity += (Math.random() - 0.44) * 1200;
    if (equity > peak) peak = equity;
    const dd = (equity - peak) / peak;
    const d = new Date(startDate);
    d.setDate(startDate.getDate() + i);
    data.push({
      date: d.toLocaleDateString("en-US", { month: "short", day: "numeric" }),
      drawdown: parseFloat((dd * 100).toFixed(2)),
    });
  }
  return data;
}

function generateMonthlyReturns(): {
  month: string;
  strategy: number;
  benchmark: number;
}[] {
  const months = [
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
  ];
  return months.map((m) => ({
    month: m,
    strategy: parseFloat(((Math.random() - 0.38) * 8).toFixed(2)),
    benchmark: parseFloat(((Math.random() - 0.42) * 5).toFixed(2)),
  }));
}

type TabId = "overview" | "risk" | "attribution" | "drawdown";

export const Portfolio: React.FC = () => {
  const { data: positions } = usePositions();
  const [activeTab, setActiveTab] = useState<TabId>("overview");

  const allPositions = positions
    ? (positions as unknown as Position[])
    : mockPositions;

  const totalMarketValue = allPositions.reduce(
    (s, p) => s + p.quantity * p.currentPrice,
    0,
  );
  const totalUnrealizedPnL = allPositions.reduce(
    (s, p) => s + p.unrealizedPnL,
    0,
  );
  const allocationData = allPositions.map((p) => ({
    name: p.ticker,
    value: p.quantity * p.currentPrice,
  }));

  const sectorData = useMemo(() => {
    const map: Record<string, number> = {};
    allPositions.forEach((p) => {
      map[p.sector] = (map[p.sector] ?? 0) + p.quantity * p.currentPrice;
    });
    return Object.entries(map).map(([name, value]) => ({ name, value }));
  }, [allPositions]);

  const drawdownData = useMemo(() => generateDrawdownData(), []);
  const monthlyReturns = useMemo(() => generateMonthlyReturns(), []);

  const tabs: { id: TabId; label: string }[] = [
    { id: "overview", label: "Overview" },
    { id: "risk", label: "Risk Metrics" },
    { id: "attribution", label: "Attribution" },
    { id: "drawdown", label: "Drawdown Analysis" },
  ];

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-start">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Portfolio</h1>
          <p className="mt-1 text-sm text-gray-500">
            Positions, risk analytics & performance attribution
          </p>
        </div>
        <div className="flex space-x-2">
          <button className="px-3 py-1.5 text-xs font-medium border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50">
            Export CSV
          </button>
          <button className="px-3 py-1.5 text-xs font-medium bg-blue-600 text-white rounded-md hover:bg-blue-700">
            Rebalance
          </button>
        </div>
      </div>

      {/* KPI bar */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
        {[
          {
            label: "Total Value",
            value: formatCurrency(125430.5),
            sub: "+2.1% today",
            color: "text-green-600",
          },
          {
            label: "Unrealized P&L",
            value: formatCurrency(totalUnrealizedPnL),
            sub: `${formatPercentage(totalUnrealizedPnL / 110000)}`,
            color: getColorForValue(totalUnrealizedPnL),
          },
          {
            label: "Sharpe Ratio",
            value: riskMetrics.portfolioSharpe.toFixed(2),
            sub: "annualised",
            color: "text-gray-900",
          },
          {
            label: "Max Drawdown",
            value: `-${formatPercentage(riskMetrics.maxDrawdown)}`,
            sub: "90-day window",
            color: "text-red-600",
          },
          {
            label: "Portfolio Beta",
            value: riskMetrics.portfolioBeta.toFixed(2),
            sub: "vs S&P 500",
            color: "text-gray-900",
          },
          {
            label: "VaR 95% (1d)",
            value: formatCurrency(riskMetrics.portfolioVar95),
            sub: "parametric",
            color: "text-orange-600",
          },
        ].map((m) => (
          <div key={m.label} className="bg-white shadow rounded-lg p-4">
            <p className="text-xs text-gray-500 font-medium">{m.label}</p>
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
              className={`py-3 text-sm font-medium border-b-2 transition-colors ${
                activeTab === t.id
                  ? "border-blue-600 text-blue-600"
                  : "border-transparent text-gray-500 hover:text-gray-700"
              }`}
            >
              {t.label}
            </button>
          ))}
        </nav>
      </div>

      {activeTab === "overview" && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="bg-white shadow rounded-lg p-6">
              <h2 className="text-sm font-semibold text-gray-700 mb-4 uppercase tracking-wide">
                Asset Allocation
              </h2>
              <ResponsiveContainer width="100%" height={260}>
                <PieChart>
                  <Pie
                    data={allocationData}
                    cx="50%"
                    cy="50%"
                    outerRadius={90}
                    dataKey="value"
                    label={({ name, percent }: PieLabelRenderProps) =>
                      `${name ?? ""} ${((percent ?? 0) * 100).toFixed(0)}%`
                    }
                    labelLine={false}
                  >
                    {allocationData.map((_, i) => (
                      <Cell key={i} fill={COLORS[i % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(v) => formatCurrency(Number(v))} />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div className="bg-white shadow rounded-lg p-6">
              <h2 className="text-sm font-semibold text-gray-700 mb-4 uppercase tracking-wide">
                Sector Breakdown
              </h2>
              <ResponsiveContainer width="100%" height={260}>
                <BarChart data={sectorData} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                  <XAxis
                    type="number"
                    tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`}
                    tick={{ fontSize: 11 }}
                  />
                  <YAxis
                    type="category"
                    dataKey="name"
                    width={100}
                    tick={{ fontSize: 11 }}
                  />
                  <Tooltip formatter={(v) => formatCurrency(Number(v))} />
                  <Bar dataKey="value" fill="#2563eb" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
          <div className="bg-white shadow rounded-lg overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-200 flex justify-between items-center">
              <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide">
                Positions
              </h2>
              <span className="text-xs text-gray-400">
                {allPositions.length} holdings · Total MV{" "}
                {formatCurrency(totalMarketValue)}
              </span>
            </div>
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200 text-sm">
                <thead className="bg-gray-50">
                  <tr>
                    {[
                      "Ticker",
                      "Sector",
                      "Qty",
                      "Entry",
                      "Current",
                      "Mkt Value",
                      "Unrealized P&L",
                      "Weight",
                      "Beta",
                    ].map((h) => (
                      <th
                        key={h}
                        className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase"
                      >
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {allPositions.map((p) => (
                    <tr key={p.id} className="hover:bg-gray-50">
                      <td className="px-4 py-3 font-semibold text-blue-700">
                        {p.ticker}
                      </td>
                      <td className="px-4 py-3 text-gray-500">{p.sector}</td>
                      <td className="px-4 py-3 text-gray-700">{p.quantity}</td>
                      <td className="px-4 py-3 text-gray-700">
                        {formatCurrency(p.entryPrice)}
                      </td>
                      <td className="px-4 py-3 text-gray-700">
                        {formatCurrency(p.currentPrice)}
                      </td>
                      <td className="px-4 py-3 text-gray-700">
                        {formatCurrency(p.quantity * p.currentPrice)}
                      </td>
                      <td
                        className={`px-4 py-3 font-semibold ${getColorForValue(p.unrealizedPnL)}`}
                      >
                        {formatCurrency(p.unrealizedPnL)}
                      </td>
                      <td className="px-4 py-3 text-gray-700">
                        {formatPercentage(p.weight)}
                      </td>
                      <td className="px-4 py-3 text-gray-700">
                        {p.beta.toFixed(2)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {activeTab === "risk" && (
        <div className="space-y-6">
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
            {[
              {
                label: "VaR 95% (1d)",
                value: formatCurrency(riskMetrics.portfolioVar95),
              },
              {
                label: "CVaR 95% (1d)",
                value: formatCurrency(riskMetrics.portfolioCVaR95),
              },
              {
                label: "Sortino Ratio",
                value: riskMetrics.portfolioSortino.toFixed(2),
              },
              {
                label: "Calmar Ratio",
                value: riskMetrics.calmarRatio.toFixed(2),
              },
              {
                label: "Info Ratio",
                value: riskMetrics.informationRatio.toFixed(2),
              },
              {
                label: "Tracking Error",
                value: formatPercentage(riskMetrics.trackingError),
              },
              {
                label: "Volatility (Ann.)",
                value: formatPercentage(riskMetrics.volatility),
              },
              { label: "Beta", value: riskMetrics.portfolioBeta.toFixed(2) },
              {
                label: "Max Drawdown",
                value: `-${formatPercentage(riskMetrics.maxDrawdown)}`,
              },
              {
                label: "Sharpe Ratio",
                value: riskMetrics.portfolioSharpe.toFixed(2),
              },
            ].map((m) => (
              <div key={m.label} className="bg-white shadow rounded-lg p-4">
                <p className="text-xs text-gray-500">{m.label}</p>
                <p className="text-lg font-bold text-gray-900">{m.value}</p>
              </div>
            ))}
          </div>
          <div className="bg-white shadow rounded-lg p-6">
            <h2 className="text-sm font-semibold text-gray-700 mb-4 uppercase tracking-wide">
              Per-Position VaR Contribution (95%, 1d)
            </h2>
            <ResponsiveContainer width="100%" height={240}>
              <BarChart
                data={allPositions.map((p) => ({
                  ticker: p.ticker,
                  var95: p.var95,
                }))}
              >
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="ticker" tick={{ fontSize: 12 }} />
                <YAxis tickFormatter={(v) => `$${v}`} tick={{ fontSize: 11 }} />
                <Tooltip formatter={(v) => [`$${v}`, "VaR 95%"]} />
                <Bar dataKey="var95" fill="#ef4444" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {activeTab === "attribution" && (
        <div className="space-y-6">
          <div className="bg-white shadow rounded-lg p-6">
            <h2 className="text-sm font-semibold text-gray-700 mb-4 uppercase tracking-wide">
              Sharpe Ratio Contribution by Position
            </h2>
            <ResponsiveContainer width="100%" height={240}>
              <BarChart
                data={allPositions.map((p) => ({
                  ticker: p.ticker,
                  sharpe: p.sharpeContrib,
                }))}
              >
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="ticker" tick={{ fontSize: 12 }} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip
                  formatter={(v) => [Number(v).toFixed(2), "Sharpe contrib"]}
                />
                <Bar dataKey="sharpe" fill="#10b981" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="bg-white shadow rounded-lg p-6">
            <h2 className="text-sm font-semibold text-gray-700 mb-4 uppercase tracking-wide">
              Monthly Returns vs Benchmark
            </h2>
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={monthlyReturns}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="month" tick={{ fontSize: 11 }} />
                <YAxis tickFormatter={(v) => `${v}%`} tick={{ fontSize: 11 }} />
                <Tooltip formatter={(v) => [`${Number(v).toFixed(2)}%`]} />
                <Legend />
                <Bar
                  dataKey="strategy"
                  name="Strategy"
                  fill="#2563eb"
                  radius={[3, 3, 0, 0]}
                />
                <Bar
                  dataKey="benchmark"
                  name="S&P 500"
                  fill="#9ca3af"
                  radius={[3, 3, 0, 0]}
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {activeTab === "drawdown" && (
        <div className="bg-white shadow rounded-lg p-6">
          <h2 className="text-sm font-semibold text-gray-700 mb-1 uppercase tracking-wide">
            Drawdown Chart (90-day)
          </h2>
          <p className="text-xs text-gray-400 mb-4">
            Peak-to-trough equity decline as percentage
          </p>
          <ResponsiveContainer width="100%" height={320}>
            <AreaChart data={drawdownData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" tick={{ fontSize: 10 }} interval={14} />
              <YAxis
                tickFormatter={(v) => `${v}%`}
                tick={{ fontSize: 11 }}
                domain={["auto", 0]}
              />
              <Tooltip
                formatter={(v) => [`${Number(v).toFixed(2)}%`, "Drawdown"]}
              />
              <Area
                type="monotone"
                dataKey="drawdown"
                stroke="#ef4444"
                fill="#fee2e2"
                fillOpacity={0.7}
              />
            </AreaChart>
          </ResponsiveContainer>
          <div className="mt-4 grid grid-cols-3 gap-4">
            {[
              {
                label: "Max Drawdown",
                value: `-${formatPercentage(riskMetrics.maxDrawdown)}`,
              },
              { label: "Avg Drawdown", value: "-3.2%" },
              { label: "Recovery Time (avg)", value: "8.4 days" },
            ].map((s) => (
              <div
                key={s.label}
                className="bg-red-50 rounded-lg p-3 text-center"
              >
                <p className="text-xs text-gray-500">{s.label}</p>
                <p className="font-bold text-red-700">{s.value}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
