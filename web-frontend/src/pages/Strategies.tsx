import type React from "react";
import { useState } from "react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { formatPercentage } from "../utils/format";
import type { Strategy } from "../types";

function generateEquityCurve(
  totalReturn: number,
  volatility: number,
  days = 252,
): { day: number; value: number; benchmark: number }[] {
  let equity = 100;
  let bench = 100;
  const dailyReturn = Math.pow(1 + totalReturn, 1 / days) - 1;
  const data = [{ day: 0, value: 100, benchmark: 100 }];
  for (let i = 1; i <= days; i++) {
    equity *= 1 + dailyReturn + (Math.random() - 0.5) * volatility * 0.2;
    bench *= 1 + (Math.random() - 0.48) * 0.008;
    data.push({
      day: i,
      value: parseFloat(equity.toFixed(2)),
      benchmark: parseFloat(bench.toFixed(2)),
    });
  }
  return data;
}

function generateRollingMetrics(
  days = 252,
): { day: number; sharpe: number; drawdown: number }[] {
  const data: { day: number; sharpe: number; drawdown: number }[] = [];
  let peak = 100;
  let equity = 100;
  for (let i = 0; i <= days; i++) {
    equity += (Math.random() - 0.45) * 1.2;
    if (equity > peak) peak = equity;
    data.push({
      day: i,
      sharpe: parseFloat(
        (1.5 + Math.sin(i / 30) * 0.8 + (Math.random() - 0.5) * 0.4).toFixed(2),
      ),
      drawdown: parseFloat((((equity - peak) / peak) * 100).toFixed(2)),
    });
  }
  return data;
}

const defaultStrategies: (Strategy & {
  equityCurve: ReturnType<typeof generateEquityCurve>;
  rollingMetrics: ReturnType<typeof generateRollingMetrics>;
})[] = [
  {
    id: "1",
    name: "TFT Alpha Strategy",
    type: "TFT",
    status: "active",
    description:
      "Temporal Fusion Transformer multi-horizon forecasting with attention-based feature selection across 47 financial indicators.",
    performance: {
      sharpeRatio: 2.31,
      maxDrawdown: 0.089,
      profitFactor: 3.8,
      winRate: 0.64,
      totalReturn: 0.487,
      volatility: 0.142,
      alpha: 0.094,
      beta: 0.88,
    },
    parameters: {
      lookback: 60,
      horizon: 5,
      n_heads: 8,
      dropout: 0.1,
      lr: 0.0003,
    },
    createdAt: "2023-11-01T00:00:00Z",
    updatedAt: new Date().toISOString(),
    equityCurve: generateEquityCurve(0.487, 0.142),
    rollingMetrics: generateRollingMetrics(),
  },
  {
    id: "2",
    name: "RL Portfolio Optimizer",
    type: "RL",
    status: "active",
    description:
      "Deep Deterministic Policy Gradient (DDPG) agent optimizing continuous portfolio weights across 20 liquid equities with transaction cost awareness.",
    performance: {
      sharpeRatio: 1.94,
      maxDrawdown: 0.121,
      profitFactor: 3.1,
      winRate: 0.59,
      totalReturn: 0.398,
      volatility: 0.168,
      alpha: 0.071,
      beta: 1.04,
    },
    parameters: {
      gamma: 0.99,
      tau: 0.005,
      buffer_size: 100000,
      actor_lr: 0.0001,
      critic_lr: 0.001,
    },
    createdAt: "2023-09-15T00:00:00Z",
    updatedAt: new Date().toISOString(),
    equityCurve: generateEquityCurve(0.398, 0.168),
    rollingMetrics: generateRollingMetrics(),
  },
  {
    id: "3",
    name: "Hybrid ML Ensemble",
    type: "HYBRID",
    status: "inactive",
    description:
      "Ensemble combining TFT forecasts, DDPG execution signals, and Bayesian regime detection. Best risk-adjusted returns in backtesting.",
    performance: {
      sharpeRatio: 2.71,
      maxDrawdown: 0.072,
      profitFactor: 4.4,
      winRate: 0.67,
      totalReturn: 0.561,
      volatility: 0.131,
      alpha: 0.118,
      beta: 0.81,
    },
    parameters: {
      tft_weight: 0.4,
      ddpg_weight: 0.35,
      regime_weight: 0.25,
      rebalance_freq: "weekly",
    },
    createdAt: "2024-01-10T00:00:00Z",
    updatedAt: new Date().toISOString(),
    equityCurve: generateEquityCurve(0.561, 0.131),
    rollingMetrics: generateRollingMetrics(),
  },
  {
    id: "4",
    name: "Sentiment Momentum",
    type: "SENTIMENT",
    status: "active",
    description:
      "NLP-driven strategy processing SEC 8-K filings, earnings call transcripts, and social media sentiment signals to generate momentum signals.",
    performance: {
      sharpeRatio: 1.72,
      maxDrawdown: 0.153,
      profitFactor: 2.7,
      winRate: 0.55,
      totalReturn: 0.312,
      volatility: 0.187,
      alpha: 0.052,
      beta: 1.18,
    },
    parameters: {
      sentiment_window: 5,
      signal_threshold: 0.65,
      stop_loss: 0.05,
      max_position: 0.1,
    },
    createdAt: "2024-02-20T00:00:00Z",
    updatedAt: new Date().toISOString(),
    equityCurve: generateEquityCurve(0.312, 0.187),
    rollingMetrics: generateRollingMetrics(),
  },
];

type ViewMode = "cards" | "comparison";

export const Strategies: React.FC = () => {
  const [strategies, setStrategies] = useState(defaultStrategies);
  const [selectedStrategy, setSelectedStrategy] = useState<
    (typeof defaultStrategies)[0] | null
  >(null);
  const [viewMode, setViewMode] = useState<ViewMode>("cards");
  const [detailTab, setDetailTab] = useState<"equity" | "rolling" | "params">(
    "equity",
  );
  const [paramEdits, setParamEdits] = useState<Record<string, string>>({});

  const toggleStatus = (id: string) => {
    setStrategies((prev) =>
      prev.map((s) =>
        s.id === id
          ? { ...s, status: s.status === "active" ? "inactive" : "active" }
          : s,
      ),
    );
  };

  const activeStrategies = strategies.filter((s) => s.status === "active");
  const comparisonData = strategies.map((s) => ({
    name: s.name.replace("Strategy", "").replace("Optimizer", "").trim(),
    sharpe: s.performance.sharpeRatio,
    return: parseFloat((s.performance.totalReturn * 100).toFixed(1)),
    drawdown: parseFloat((s.performance.maxDrawdown * 100).toFixed(1)),
    winRate: parseFloat((s.performance.winRate * 100).toFixed(1)),
  }));

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Strategies</h1>
          <p className="mt-1 text-sm text-gray-500">
            {activeStrategies.length} active · {strategies.length} total
          </p>
        </div>
        <div className="flex items-center space-x-3">
          <div className="flex rounded-md shadow-sm border border-gray-300 overflow-hidden">
            {(["cards", "comparison"] as ViewMode[]).map((v) => (
              <button
                key={v}
                onClick={() => setViewMode(v)}
                className={`px-3 py-1.5 text-xs font-medium capitalize ${viewMode === v ? "bg-blue-600 text-white" : "bg-white text-gray-700 hover:bg-gray-50"}`}
              >
                {v}
              </button>
            ))}
          </div>
          <button className="inline-flex items-center px-4 py-2 text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700">
            + New Strategy
          </button>
        </div>
      </div>

      {viewMode === "comparison" ? (
        <div className="space-y-6">
          <div className="bg-white shadow rounded-lg p-6">
            <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide mb-4">
              Sharpe Ratio Comparison
            </h2>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={comparisonData} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                <XAxis type="number" domain={[0, 3]} tick={{ fontSize: 11 }} />
                <YAxis
                  type="category"
                  dataKey="name"
                  width={140}
                  tick={{ fontSize: 11 }}
                />
                <Tooltip />
                <Bar
                  dataKey="sharpe"
                  name="Sharpe Ratio"
                  fill="#2563eb"
                  radius={[0, 4, 4, 0]}
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="bg-white shadow rounded-lg p-6 overflow-x-auto">
            <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide mb-4">
              Strategy Scorecard
            </h2>
            <table className="min-w-full text-sm">
              <thead>
                <tr className="bg-gray-50">
                  {[
                    "Strategy",
                    "Sharpe",
                    "Total Return",
                    "Max DD",
                    "Win Rate",
                    "Alpha",
                    "Beta",
                    "Status",
                  ].map((h) => (
                    <th
                      key={h}
                      className="px-4 py-2 text-xs font-medium text-gray-500 uppercase text-left"
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {strategies.map((s) => (
                  <tr key={s.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 font-medium text-gray-900">
                      {s.name}
                    </td>
                    <td className="px-4 py-3 text-blue-700 font-semibold">
                      {s.performance.sharpeRatio.toFixed(2)}
                    </td>
                    <td className="px-4 py-3 text-green-700">
                      {formatPercentage(s.performance.totalReturn)}
                    </td>
                    <td className="px-4 py-3 text-red-600">
                      -{formatPercentage(s.performance.maxDrawdown)}
                    </td>
                    <td className="px-4 py-3">
                      {formatPercentage(s.performance.winRate)}
                    </td>
                    <td className="px-4 py-3">
                      {formatPercentage(s.performance.alpha)}
                    </td>
                    <td className="px-4 py-3">
                      {s.performance.beta.toFixed(2)}
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`px-2 py-0.5 rounded-full text-xs font-medium ${s.status === "active" ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-600"}`}
                      >
                        {s.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
          {strategies.map((strategy) => (
            <div
              key={strategy.id}
              className="bg-white shadow rounded-lg overflow-hidden"
            >
              <div className="p-5">
                <div className="flex items-start justify-between mb-2">
                  <div>
                    <h3 className="text-base font-semibold text-gray-900">
                      {strategy.name}
                    </h3>
                    <span className="text-xs text-gray-400">
                      {strategy.type}
                    </span>
                  </div>
                  <span
                    className={`px-2.5 py-0.5 rounded-full text-xs font-medium ${strategy.status === "active" ? "bg-green-100 text-green-800" : "bg-gray-100 text-gray-600"}`}
                  >
                    {strategy.status}
                  </span>
                </div>
                <p className="text-xs text-gray-500 mb-4">
                  {strategy.description}
                </p>
                {/* Mini equity curve */}
                <div className="h-24 mb-4">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart
                      data={strategy.equityCurve.filter((_, i) => i % 5 === 0)}
                    >
                      <Area
                        type="monotone"
                        dataKey="value"
                        stroke="#2563eb"
                        fill="#eff6ff"
                        strokeWidth={1.5}
                        dot={false}
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
                <div className="grid grid-cols-4 gap-2 text-center mb-4">
                  {[
                    {
                      label: "Sharpe",
                      value: strategy.performance.sharpeRatio.toFixed(2),
                    },
                    {
                      label: "Return",
                      value: formatPercentage(strategy.performance.totalReturn),
                    },
                    {
                      label: "Max DD",
                      value: `-${formatPercentage(strategy.performance.maxDrawdown)}`,
                    },
                    {
                      label: "Win %",
                      value: formatPercentage(strategy.performance.winRate),
                    },
                  ].map((m) => (
                    <div key={m.label} className="bg-gray-50 rounded p-2">
                      <p className="text-xs text-gray-400">{m.label}</p>
                      <p className="text-sm font-semibold text-gray-900">
                        {m.value}
                      </p>
                    </div>
                  ))}
                </div>
                <div className="flex space-x-2">
                  <button
                    onClick={() => {
                      setSelectedStrategy(strategy);
                      setDetailTab("equity");
                    }}
                    className="flex-1 py-1.5 text-xs font-medium border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
                  >
                    View Details
                  </button>
                  <button
                    onClick={() => toggleStatus(strategy.id)}
                    className={`flex-1 py-1.5 text-xs font-medium rounded-md text-white ${strategy.status === "active" ? "bg-red-500 hover:bg-red-600" : "bg-green-600 hover:bg-green-700"}`}
                  >
                    {strategy.status === "active" ? "Deactivate" : "Activate"}
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Detail Modal */}
      {selectedStrategy && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-60 p-4"
          onClick={() => setSelectedStrategy(null)}
        >
          <div
            className="bg-white rounded-xl shadow-2xl w-full max-w-3xl max-h-screen overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex justify-between items-start p-6 border-b border-gray-200">
              <div>
                <h2 className="text-xl font-bold text-gray-900">
                  {selectedStrategy.name}
                </h2>
                <p className="text-sm text-gray-500 mt-1">
                  {selectedStrategy.description}
                </p>
              </div>
              <button
                onClick={() => setSelectedStrategy(null)}
                className="text-gray-400 hover:text-gray-600 ml-4"
              >
                <svg
                  className="h-6 w-6"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M6 18L18 6M6 6l12 12"
                  />
                </svg>
              </button>
            </div>
            <div className="border-b border-gray-200 px-6">
              <nav className="flex space-x-6">
                {(["equity", "rolling", "params"] as const).map((t) => (
                  <button
                    key={t}
                    onClick={() => setDetailTab(t)}
                    className={`py-3 text-sm font-medium border-b-2 capitalize transition-colors ${detailTab === t ? "border-blue-600 text-blue-600" : "border-transparent text-gray-500 hover:text-gray-700"}`}
                  >
                    {t === "equity"
                      ? "Equity Curve"
                      : t === "rolling"
                        ? "Rolling Metrics"
                        : "Parameters"}
                  </button>
                ))}
              </nav>
            </div>
            <div className="p-6">
              {detailTab === "equity" && (
                <div>
                  <div className="grid grid-cols-4 gap-3 mb-6">
                    {[
                      {
                        label: "Total Return",
                        value: formatPercentage(
                          selectedStrategy.performance.totalReturn,
                        ),
                        color: "text-green-700",
                      },
                      {
                        label: "Sharpe",
                        value:
                          selectedStrategy.performance.sharpeRatio.toFixed(2),
                        color: "text-blue-700",
                      },
                      {
                        label: "Max DD",
                        value: `-${formatPercentage(selectedStrategy.performance.maxDrawdown)}`,
                        color: "text-red-600",
                      },
                      {
                        label: "Alpha",
                        value: formatPercentage(
                          selectedStrategy.performance.alpha,
                        ),
                        color: "text-purple-700",
                      },
                    ].map((m) => (
                      <div
                        key={m.label}
                        className="bg-gray-50 rounded-lg p-3 text-center"
                      >
                        <p className="text-xs text-gray-500">{m.label}</p>
                        <p className={`text-lg font-bold ${m.color}`}>
                          {m.value}
                        </p>
                      </div>
                    ))}
                  </div>
                  <ResponsiveContainer width="100%" height={280}>
                    <AreaChart
                      data={selectedStrategy.equityCurve.filter(
                        (_, i) => i % 2 === 0,
                      )}
                    >
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
                      <YAxis
                        tick={{ fontSize: 11 }}
                        domain={["auto", "auto"]}
                      />
                      <Tooltip
                        formatter={(v, n) => [
                          Number(v).toFixed(2),
                          n === "value" ? "Strategy" : "Benchmark",
                        ]}
                      />
                      <Legend />
                      <Area
                        type="monotone"
                        dataKey="benchmark"
                        name="S&P 500"
                        stroke="#9ca3af"
                        fill="#f3f4f6"
                        fillOpacity={0.4}
                        dot={false}
                      />
                      <Area
                        type="monotone"
                        dataKey="value"
                        name="Strategy"
                        stroke="#2563eb"
                        fill="#eff6ff"
                        fillOpacity={0.6}
                        dot={false}
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              )}
              {detailTab === "rolling" && (
                <div className="space-y-6">
                  <div>
                    <p className="text-xs text-gray-500 mb-2">
                      Rolling 30-day Sharpe Ratio
                    </p>
                    <ResponsiveContainer width="100%" height={180}>
                      <LineChart
                        data={selectedStrategy.rollingMetrics.filter(
                          (_, i) => i % 3 === 0,
                        )}
                      >
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="day" tick={{ fontSize: 10 }} />
                        <YAxis tick={{ fontSize: 11 }} />
                        <Tooltip />
                        <Line
                          type="monotone"
                          dataKey="sharpe"
                          stroke="#2563eb"
                          dot={false}
                          strokeWidth={2}
                        />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                  <div>
                    <p className="text-xs text-gray-500 mb-2">
                      Rolling Drawdown (%)
                    </p>
                    <ResponsiveContainer width="100%" height={180}>
                      <AreaChart
                        data={selectedStrategy.rollingMetrics.filter(
                          (_, i) => i % 3 === 0,
                        )}
                      >
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="day" tick={{ fontSize: 10 }} />
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
              {detailTab === "params" && (
                <div>
                  <p className="text-xs text-gray-500 mb-4">
                    Edit strategy hyperparameters and save to trigger
                    re-training.
                  </p>
                  <div className="space-y-3">
                    {Object.entries(selectedStrategy.parameters).map(
                      ([key, value]) => (
                        <div
                          key={key}
                          className="flex items-center justify-between bg-gray-50 rounded-lg px-4 py-3"
                        >
                          <span className="text-sm font-mono text-gray-700">
                            {key}
                          </span>
                          <input
                            type="text"
                            value={paramEdits[key] ?? String(value)}
                            onChange={(e) =>
                              setParamEdits((prev) => ({
                                ...prev,
                                [key]: e.target.value,
                              }))
                            }
                            className="w-32 text-sm text-right border border-gray-300 rounded-md px-2 py-1 focus:outline-none focus:ring-1 focus:ring-blue-500"
                          />
                        </div>
                      ),
                    )}
                  </div>
                  <div className="mt-4 flex justify-end space-x-3">
                    <button
                      onClick={() => setParamEdits({})}
                      className="px-4 py-2 text-sm border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
                    >
                      Reset
                    </button>
                    <button className="px-4 py-2 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700">
                      Save & Retrain
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
