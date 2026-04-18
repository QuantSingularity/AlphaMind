import type React from "react";
import { useMemo, useState } from "react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ComposedChart,
  Legend,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Scatter,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { formatCurrency, formatPercentage } from "../utils/format";

interface BacktestConfig {
  strategyId: string;
  startDate: string;
  endDate: string;
  initialCapital: number;
  benchmark: string;
  transactionCost: number;
  slippage: number;
}

interface TradeRecord {
  date: string;
  ticker: string;
  side: "BUY" | "SELL";
  qty: number;
  price: number;
  pnl: number;
}

interface BacktestResult {
  equityCurve: {
    date: string;
    equity: number;
    benchmark: number;
    drawdown: number;
  }[];
  trades: TradeRecord[];
  totalReturn: number;
  annualisedReturn: number;
  sharpeRatio: number;
  sortinoRatio: number;
  calmarRatio: number;
  maxDrawdown: number;
  maxDrawdownDuration: number;
  winRate: number;
  profitFactor: number;
  totalTrades: number;
  avgWin: number;
  avgLoss: number;
  bestMonth: number;
  worstMonth: number;
  finalCapital: number;
  alpha: number;
  beta: number;
  informationRatio: number;
  benchmarkReturn: number;
  monthlyReturns: { month: string; strategy: number; benchmark: number }[];
  rollingSharpe: { day: number; sharpe: number }[];
}

const mockStrategies = [
  { id: "1", name: "TFT Alpha Strategy" },
  { id: "2", name: "RL Portfolio Optimizer" },
  { id: "3", name: "Hybrid ML Ensemble" },
  { id: "4", name: "Sentiment Momentum" },
];

// Deterministic, realistic results keyed by strategy
const STRATEGY_PROFILES: Record<
  string,
  {
    drift: number;
    vol: number;
    sharpe: number;
    winRate: number;
    alpha: number;
    beta: number;
  }
> = {
  "1": {
    drift: 0.00192,
    vol: 0.0089,
    sharpe: 2.31,
    winRate: 0.64,
    alpha: 0.094,
    beta: 0.88,
  },
  "2": {
    drift: 0.00153,
    vol: 0.0105,
    sharpe: 1.94,
    winRate: 0.59,
    alpha: 0.071,
    beta: 1.04,
  },
  "3": {
    drift: 0.00221,
    vol: 0.0082,
    sharpe: 2.71,
    winRate: 0.67,
    alpha: 0.118,
    beta: 0.81,
  },
  "4": {
    drift: 0.00119,
    vol: 0.0117,
    sharpe: 1.72,
    winRate: 0.55,
    alpha: 0.052,
    beta: 1.18,
  },
};

function generateBacktestResult(config: BacktestConfig): BacktestResult {
  const profile =
    STRATEGY_PROFILES[config.strategyId] ?? STRATEGY_PROFILES["1"];
  const start = new Date(config.startDate);
  const end = new Date(config.endDate);
  const totalDays = Math.max(
    30,
    Math.ceil((end.getTime() - start.getTime()) / 86400000),
  );

  // Seed deterministic sequence using strategy id + dates
  let seed = parseInt(config.strategyId) * 137 + totalDays;
  const rng = () => {
    seed = (seed * 1664525 + 1013904223) & 0xffffffff;
    return (seed >>> 0) / 0xffffffff;
  };

  let equity = config.initialCapital;
  let benchmark = config.initialCapital;
  let peak = equity;
  let maxDD = 0;
  const curve: BacktestResult["equityCurve"] = [];
  const trades: TradeRecord[] = [];
  const tickers = ["AAPL", "MSFT", "GOOGL", "TSLA", "JPM", "NVDA"];

  for (let i = 0; i <= totalDays; i++) {
    const stratReturn = profile.drift + (rng() - 0.5) * profile.vol * 3.5;
    const benchReturn = 0.00045 + (rng() - 0.5) * 0.008;
    equity *=
      1 + stratReturn - config.transactionCost / 100 - config.slippage / 100;
    benchmark *= 1 + benchReturn;
    if (equity > peak) peak = equity;
    const dd = (equity - peak) / peak;
    if (dd < maxDD) maxDD = dd;

    const date = new Date(start);
    date.setDate(start.getDate() + i);
    const dateStr = date.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
    });
    curve.push({
      date: dateStr,
      equity: Math.round(equity),
      benchmark: Math.round(benchmark),
      drawdown: parseFloat((dd * 100).toFixed(2)),
    });

    // Generate trades
    if (i > 0 && rng() > 0.82) {
      const side = rng() > 0.5 ? "BUY" : "SELL";
      const ticker = tickers[Math.floor(rng() * tickers.length)];
      const price = 100 + rng() * 400;
      const qty = Math.floor(rng() * 50 + 5);
      const pnl =
        side === "SELL"
          ? (rng() > 1 - profile.winRate ? 1 : -1) * rng() * price * 0.04 * qty
          : 0;
      trades.push({
        date: dateStr,
        ticker,
        side,
        qty,
        price: parseFloat(price.toFixed(2)),
        pnl: parseFloat(pnl.toFixed(2)),
      });
    }
  }

  const finalCapital = curve[curve.length - 1]?.equity ?? config.initialCapital;
  const totalReturn =
    (finalCapital - config.initialCapital) / config.initialCapital;
  const years = totalDays / 252;
  const annualisedReturn =
    Math.pow(1 + totalReturn, 1 / Math.max(years, 0.1)) - 1;
  const benchReturn =
    (curve[curve.length - 1]?.benchmark ?? config.initialCapital) /
      config.initialCapital -
    1;

  const winTrades = trades.filter((t) => t.pnl > 0);
  const lossTrades = trades.filter((t) => t.pnl < 0);
  const avgWin = winTrades.length
    ? winTrades.reduce((s, t) => s + t.pnl, 0) / winTrades.length
    : 0;
  const avgLoss = lossTrades.length
    ? Math.abs(lossTrades.reduce((s, t) => s + t.pnl, 0) / lossTrades.length)
    : 0;

  // Monthly returns
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
  const monthlyReturns = months.map((m) => ({
    month: m,
    strategy: parseFloat(
      ((rng() - (1 - profile.winRate) * 0.8) * 7).toFixed(2),
    ),
    benchmark: parseFloat(((rng() - 0.44) * 4).toFixed(2)),
  }));

  const bestMonth = Math.max(...monthlyReturns.map((r) => r.strategy));
  const worstMonth = Math.min(...monthlyReturns.map((r) => r.strategy));

  // Rolling Sharpe
  const rollingSharpe = curve
    .filter((_, i) => i % 5 === 0)
    .map((_, i) => ({
      day: i * 5,
      sharpe: parseFloat(
        (profile.sharpe + Math.sin(i / 8) * 0.6 + (rng() - 0.5) * 0.3).toFixed(
          2,
        ),
      ),
    }));

  return {
    equityCurve: curve,
    trades: trades.slice(0, 50),
    totalReturn,
    annualisedReturn,
    sharpeRatio: profile.sharpe,
    sortinoRatio: profile.sharpe * 1.38,
    calmarRatio: annualisedReturn / Math.abs(maxDD || 0.01),
    maxDrawdown: Math.abs(maxDD),
    maxDrawdownDuration: Math.floor(totalDays * 0.12),
    winRate: profile.winRate,
    profitFactor:
      avgLoss > 0
        ? (avgWin * winTrades.length) / (avgLoss * lossTrades.length)
        : 2.5,
    totalTrades: trades.length,
    avgWin,
    avgLoss,
    bestMonth,
    worstMonth,
    finalCapital,
    alpha: profile.alpha,
    beta: profile.beta,
    informationRatio:
      (totalReturn - benchReturn) / (profile.vol * Math.sqrt(252) * 0.8),
    benchmarkReturn: benchReturn,
    monthlyReturns,
    rollingSharpe,
  };
}

type TabId = "tearsheet" | "trades" | "monthly" | "rolling";

export const Backtest: React.FC = () => {
  const [config, setConfig] = useState<BacktestConfig>({
    strategyId: "1",
    startDate: "2022-01-01",
    endDate: "2024-12-31",
    initialCapital: 100000,
    benchmark: "SPY",
    transactionCost: 0.05,
    slippage: 0.02,
  });
  const [result, setResult] = useState<BacktestResult | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<TabId>("tearsheet");

  const handleRun = async () => {
    if (new Date(config.startDate) >= new Date(config.endDate)) {
      setError("Start date must be before end date.");
      return;
    }
    if (config.initialCapital < 1000) {
      setError("Initial capital must be at least $1,000.");
      return;
    }
    setError(null);
    setIsRunning(true);
    setResult(null);
    await new Promise((r) => setTimeout(r, 1200));
    setResult(generateBacktestResult(config));
    setIsRunning(false);
    setActiveTab("tearsheet");
  };

  const stratName =
    mockStrategies.find((s) => s.id === config.strategyId)?.name ?? "";
  const curveSubset = useMemo(
    () =>
      result?.equityCurve.filter(
        (_, i) =>
          i % Math.max(1, Math.floor(result.equityCurve.length / 200)) === 0,
      ) ?? [],
    [result],
  );

  const tabs: { id: TabId; label: string }[] = [
    { id: "tearsheet", label: "Tearsheet" },
    { id: "monthly", label: "Monthly Returns" },
    { id: "rolling", label: "Rolling Sharpe" },
    { id: "trades", label: "Trade Log" },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Backtesting</h1>
        <p className="mt-1 text-sm text-gray-500">
          Run historical simulations and analyse strategy performance tearsheets
        </p>
      </div>

      {/* Config panel */}
      <div className="bg-white shadow rounded-lg p-6">
        <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide mb-4">
          Configuration
        </h2>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
          <div className="col-span-2 sm:col-span-1">
            <label className="block text-xs font-medium text-gray-600 mb-1">
              Strategy
            </label>
            <select
              value={config.strategyId}
              onChange={(e) =>
                setConfig((p) => ({ ...p, strategyId: e.target.value }))
              }
              className="block w-full border border-gray-300 rounded-md py-2 px-3 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
            >
              {mockStrategies.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">
              Start Date
            </label>
            <input
              type="date"
              value={config.startDate}
              onChange={(e) =>
                setConfig((p) => ({ ...p, startDate: e.target.value }))
              }
              className="block w-full border border-gray-300 rounded-md py-2 px-3 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">
              End Date
            </label>
            <input
              type="date"
              value={config.endDate}
              onChange={(e) =>
                setConfig((p) => ({ ...p, endDate: e.target.value }))
              }
              className="block w-full border border-gray-300 rounded-md py-2 px-3 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">
              Capital ($)
            </label>
            <input
              type="number"
              min={1000}
              step={5000}
              value={config.initialCapital}
              onChange={(e) =>
                setConfig((p) => ({
                  ...p,
                  initialCapital: Number(e.target.value),
                }))
              }
              className="block w-full border border-gray-300 rounded-md py-2 px-3 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">
              Tx Cost (bps)
            </label>
            <input
              type="number"
              min={0}
              max={50}
              step={0.5}
              value={config.transactionCost}
              onChange={(e) =>
                setConfig((p) => ({
                  ...p,
                  transactionCost: Number(e.target.value),
                }))
              }
              className="block w-full border border-gray-300 rounded-md py-2 px-3 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">
              Slippage (bps)
            </label>
            <input
              type="number"
              min={0}
              max={20}
              step={0.5}
              value={config.slippage}
              onChange={(e) =>
                setConfig((p) => ({ ...p, slippage: Number(e.target.value) }))
              }
              className="block w-full border border-gray-300 rounded-md py-2 px-3 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>
        </div>

        {error && (
          <p className="mt-3 text-sm text-red-600 bg-red-50 border border-red-200 rounded-md px-3 py-2">
            {error}
          </p>
        )}

        <div className="mt-4 flex space-x-3">
          <button
            onClick={handleRun}
            disabled={isRunning}
            className="inline-flex items-center px-5 py-2 text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isRunning ? (
              <>
                <span className="animate-spin mr-2">⟳</span> Running…
              </>
            ) : (
              "▶  Run Backtest"
            )}
          </button>
          {result && (
            <button
              onClick={() => setResult(null)}
              className="px-4 py-2 text-sm border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
            >
              Reset
            </button>
          )}
        </div>
      </div>

      {result && (
        <>
          {/* Strategy / period header */}
          <div className="bg-blue-50 border border-blue-200 rounded-lg px-5 py-3 flex items-center justify-between">
            <div>
              <span className="text-sm font-semibold text-blue-800">
                {stratName}
              </span>
              <span className="text-xs text-blue-500 ml-3">
                {config.startDate} → {config.endDate} · {result.totalTrades}{" "}
                trades · Initial capital {formatCurrency(config.initialCapital)}
              </span>
            </div>
            <span
              className={`text-lg font-bold ${result.totalReturn >= 0 ? "text-green-700" : "text-red-700"}`}
            >
              {result.totalReturn >= 0 ? "+" : ""}
              {formatPercentage(result.totalReturn)} total return
            </span>
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

          {activeTab === "tearsheet" && (
            <div className="space-y-6">
              {/* KPI Grid */}
              <div className="grid grid-cols-3 sm:grid-cols-4 lg:grid-cols-6 gap-3">
                {[
                  {
                    label: "Total Return",
                    value: formatPercentage(result.totalReturn),
                    color:
                      result.totalReturn >= 0
                        ? "text-green-700"
                        : "text-red-700",
                  },
                  {
                    label: "Ann. Return",
                    value: formatPercentage(result.annualisedReturn),
                    color: "text-green-700",
                  },
                  {
                    label: "Benchmark",
                    value: formatPercentage(result.benchmarkReturn),
                    color: "text-gray-700",
                  },
                  {
                    label: "Sharpe",
                    value: result.sharpeRatio.toFixed(2),
                    color: "text-blue-700",
                  },
                  {
                    label: "Sortino",
                    value: result.sortinoRatio.toFixed(2),
                    color: "text-blue-700",
                  },
                  {
                    label: "Calmar",
                    value: result.calmarRatio.toFixed(2),
                    color: "text-blue-700",
                  },
                  {
                    label: "Max Drawdown",
                    value: `-${formatPercentage(result.maxDrawdown)}`,
                    color: "text-red-600",
                  },
                  {
                    label: "Max DD Days",
                    value: `${result.maxDrawdownDuration}d`,
                    color: "text-red-500",
                  },
                  {
                    label: "Win Rate",
                    value: formatPercentage(result.winRate),
                    color: "text-gray-800",
                  },
                  {
                    label: "Profit Factor",
                    value: result.profitFactor.toFixed(2),
                    color: "text-gray-800",
                  },
                  {
                    label: "Alpha",
                    value: formatPercentage(result.alpha),
                    color: "text-purple-700",
                  },
                  {
                    label: "Beta",
                    value: result.beta.toFixed(2),
                    color: "text-gray-700",
                  },
                  {
                    label: "Info Ratio",
                    value: result.informationRatio.toFixed(2),
                    color: "text-gray-700",
                  },
                  {
                    label: "Avg Win",
                    value: formatCurrency(result.avgWin),
                    color: "text-green-600",
                  },
                  {
                    label: "Avg Loss",
                    value: `-${formatCurrency(result.avgLoss)}`,
                    color: "text-red-500",
                  },
                  {
                    label: "Final Capital",
                    value: formatCurrency(result.finalCapital),
                    color:
                      result.finalCapital >= config.initialCapital
                        ? "text-green-700"
                        : "text-red-700",
                  },
                  {
                    label: "Best Month",
                    value: `+${result.bestMonth.toFixed(1)}%`,
                    color: "text-green-700",
                  },
                  {
                    label: "Worst Month",
                    value: `${result.worstMonth.toFixed(1)}%`,
                    color: "text-red-600",
                  },
                ].map((m) => (
                  <div key={m.label} className="bg-white shadow rounded-lg p-3">
                    <p className="text-xs text-gray-400 leading-tight">
                      {m.label}
                    </p>
                    <p className={`text-sm font-bold mt-0.5 ${m.color}`}>
                      {m.value}
                    </p>
                  </div>
                ))}
              </div>

              {/* Equity curve */}
              <div className="bg-white shadow rounded-lg p-6">
                <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide mb-4">
                  Equity Curve vs Benchmark
                </h2>
                <ResponsiveContainer width="100%" height={300}>
                  <AreaChart data={curveSubset}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis
                      dataKey="date"
                      tick={{ fontSize: 9 }}
                      interval={Math.floor(curveSubset.length / 7)}
                    />
                    <YAxis
                      tickFormatter={(v: number) =>
                        `$${(v / 1000).toFixed(0)}k`
                      }
                      tick={{ fontSize: 11 }}
                    />
                    <Tooltip formatter={(v) => [formatCurrency(Number(v))]} />
                    <Legend />
                    <Area
                      type="monotone"
                      dataKey="benchmark"
                      name="S&P 500"
                      stroke="#9ca3af"
                      fill="#f3f4f6"
                      fillOpacity={0.4}
                      dot={false}
                      strokeWidth={1.5}
                    />
                    <Area
                      type="monotone"
                      dataKey="equity"
                      name="Strategy"
                      stroke="#2563eb"
                      fill="#eff6ff"
                      fillOpacity={0.6}
                      dot={false}
                      strokeWidth={2}
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>

              {/* Drawdown */}
              <div className="bg-white shadow rounded-lg p-6">
                <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide mb-1">
                  Drawdown
                </h2>
                <p className="text-xs text-gray-400 mb-4">
                  Underwater equity curve — percentage below previous peak
                </p>
                <ResponsiveContainer width="100%" height={180}>
                  <AreaChart data={curveSubset}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis
                      dataKey="date"
                      tick={{ fontSize: 9 }}
                      interval={Math.floor(curveSubset.length / 7)}
                    />
                    <YAxis
                      tickFormatter={(v) => `${v}%`}
                      tick={{ fontSize: 11 }}
                      domain={["auto", 0]}
                    />
                    <Tooltip
                      formatter={(v) => [
                        `${Number(v).toFixed(2)}%`,
                        "Drawdown",
                      ]}
                    />
                    <ReferenceLine
                      y={-result.maxDrawdown * 100}
                      stroke="#ef4444"
                      strokeDasharray="4 4"
                      label={{ value: "Max DD", fill: "#ef4444", fontSize: 11 }}
                    />
                    <Area
                      type="monotone"
                      dataKey="drawdown"
                      stroke="#ef4444"
                      fill="#fee2e2"
                      fillOpacity={0.7}
                      dot={false}
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}

          {activeTab === "monthly" && (
            <div className="bg-white shadow rounded-lg p-6">
              <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide mb-4">
                Monthly Returns vs Benchmark (%)
              </h2>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={result.monthlyReturns}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="month" tick={{ fontSize: 12 }} />
                  <YAxis
                    tickFormatter={(v) => `${v}%`}
                    tick={{ fontSize: 11 }}
                  />
                  <Tooltip formatter={(v) => [`${Number(v).toFixed(2)}%`]} />
                  <Legend />
                  <ReferenceLine y={0} stroke="#6b7280" />
                  <Bar dataKey="strategy" name="Strategy" radius={[3, 3, 0, 0]}>
                    {result.monthlyReturns.map((r, i) => (
                      <Cell
                        key={i}
                        fill={r.strategy >= 0 ? "#2563eb" : "#ef4444"}
                      />
                    ))}
                  </Bar>
                  <Bar
                    dataKey="benchmark"
                    name="S&P 500"
                    fill="#9ca3af"
                    radius={[3, 3, 0, 0]}
                  />
                </BarChart>
              </ResponsiveContainer>
              <div className="mt-4 grid grid-cols-4 gap-3">
                {[
                  {
                    label: "Best Month",
                    value: `+${result.bestMonth.toFixed(2)}%`,
                    color: "text-green-700",
                  },
                  {
                    label: "Worst Month",
                    value: `${result.worstMonth.toFixed(2)}%`,
                    color: "text-red-600",
                  },
                  {
                    label: "Positive Months",
                    value: `${result.monthlyReturns.filter((r) => r.strategy > 0).length}/12`,
                    color: "text-gray-800",
                  },
                  {
                    label: "Avg Monthly",
                    value: `${((result.annualisedReturn / 12) * 100).toFixed(2)}%`,
                    color: "text-blue-700",
                  },
                ].map((m) => (
                  <div
                    key={m.label}
                    className="bg-gray-50 rounded-lg p-3 text-center"
                  >
                    <p className="text-xs text-gray-500">{m.label}</p>
                    <p className={`text-base font-bold ${m.color}`}>
                      {m.value}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {activeTab === "rolling" && (
            <div className="bg-white shadow rounded-lg p-6">
              <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide mb-1">
                Rolling 30-Day Sharpe Ratio
              </h2>
              <p className="text-xs text-gray-400 mb-4">
                Values above 1.0 indicate risk-adjusted outperformance over the
                preceding month
              </p>
              <ResponsiveContainer width="100%" height={300}>
                <ComposedChart data={result.rollingSharpe}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis
                    dataKey="day"
                    tick={{ fontSize: 10 }}
                    label={{
                      value: "Trading Day",
                      position: "insideBottom",
                      offset: -2,
                      fontSize: 11,
                    }}
                  />
                  <YAxis tick={{ fontSize: 11 }} domain={["auto", "auto"]} />
                  <Tooltip
                    formatter={(v) => [Number(v).toFixed(2), "Rolling Sharpe"]}
                  />
                  <ReferenceLine
                    y={1}
                    stroke="#10b981"
                    strokeDasharray="4 4"
                    label={{
                      value: "Sharpe = 1",
                      fill: "#10b981",
                      fontSize: 11,
                    }}
                  />
                  <ReferenceLine y={0} stroke="#6b7280" />
                  <Area
                    type="monotone"
                    dataKey="sharpe"
                    stroke="#2563eb"
                    fill="#eff6ff"
                    fillOpacity={0.4}
                    dot={false}
                    strokeWidth={2}
                  />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
          )}

          {activeTab === "trades" && (
            <div className="bg-white shadow rounded-lg overflow-hidden">
              <div className="px-6 py-4 border-b border-gray-200 flex justify-between items-center">
                <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide">
                  Trade Log
                </h2>
                <span className="text-xs text-gray-400">
                  {result.trades.length} trades shown (first 50)
                </span>
              </div>
              <div className="overflow-x-auto">
                <table className="min-w-full text-sm divide-y divide-gray-100">
                  <thead className="bg-gray-50">
                    <tr>
                      {["Date", "Ticker", "Side", "Qty", "Price", "P&L"].map(
                        (h) => (
                          <th
                            key={h}
                            className="px-5 py-3 text-left text-xs font-medium text-gray-500 uppercase"
                          >
                            {h}
                          </th>
                        ),
                      )}
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-100">
                    {result.trades.map((t, i) => (
                      <tr key={i} className="hover:bg-gray-50">
                        <td className="px-5 py-2.5 text-gray-500">{t.date}</td>
                        <td className="px-5 py-2.5 font-semibold text-gray-900">
                          {t.ticker}
                        </td>
                        <td className="px-5 py-2.5">
                          <span
                            className={`px-2 py-0.5 rounded text-xs font-semibold ${t.side === "BUY" ? "bg-blue-100 text-blue-700" : "bg-orange-100 text-orange-700"}`}
                          >
                            {t.side}
                          </span>
                        </td>
                        <td className="px-5 py-2.5 text-gray-700">{t.qty}</td>
                        <td className="px-5 py-2.5 text-gray-700">
                          {formatCurrency(t.price)}
                        </td>
                        <td
                          className={`px-5 py-2.5 font-semibold ${t.pnl >= 0 ? "text-green-700" : "text-red-600"}`}
                        >
                          {t.pnl === 0 ? "—" : formatCurrency(t.pnl)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
};
