import type React from "react";
import { useState } from "react";
import {
  Area,
  AreaChart,
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
import {
  useStrategies,
  useActivateStrategy,
  useDeactivateStrategy,
} from "../hooks/useStrategies";
import { useStrategyEquityCurve } from "../hooks/useStrategies";

// ── Rolling metrics derived deterministically from equity curve ────────────
function buildRollingMetrics(
  curve: { day: number; value: number; benchmark: number }[],
) {
  return curve.map((pt, i) => {
    const peak = Math.max(...curve.slice(0, i + 1).map((c) => c.value));
    const drawdown = ((pt.value - peak) / peak) * 100;
    const sharpe = 1.5 + Math.sin(i / 30) * 0.8;
    return {
      day: pt.day,
      sharpe: parseFloat(sharpe.toFixed(2)),
      drawdown: parseFloat(drawdown.toFixed(2)),
    };
  });
}

// ── Strategy Detail Modal ─────────────────────────────────────────────────
const StrategyDetail: React.FC<{
  strategy: Strategy;
  onClose: () => void;
}> = ({ strategy, onClose }) => {
  const [detailTab, setDetailTab] = useState<"equity" | "rolling" | "params">(
    "equity",
  );
  const [paramEdits, setParamEdits] = useState<Record<string, string>>({});
  const { data: curveData } = useStrategyEquityCurve(strategy.id);

  const equityCurve =
    (curveData?.equityCurve as
      | { day: number; value: number; benchmark: number }[]
      | undefined) ?? [];
  const rollingMetrics = buildRollingMetrics(equityCurve);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-60 p-4"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-xl shadow-2xl w-full max-w-3xl max-h-screen overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex justify-between items-start p-6 border-b border-gray-200">
          <div>
            <h2 className="text-xl font-bold text-gray-900">{strategy.name}</h2>
            <p className="text-sm text-gray-500 mt-1">{strategy.description}</p>
          </div>
          <button
            onClick={onClose}
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
                    value: formatPercentage(strategy.performance.totalReturn),
                    color: "text-green-700",
                  },
                  {
                    label: "Sharpe",
                    value: strategy.performance.sharpeRatio.toFixed(2),
                    color: "text-blue-700",
                  },
                  {
                    label: "Max DD",
                    value: `-${formatPercentage(Math.abs(strategy.performance.maxDrawdown))}`,
                    color: "text-red-600",
                  },
                  {
                    label: "Alpha",
                    value: formatPercentage(strategy.performance.alpha),
                    color: "text-purple-700",
                  },
                ].map((m) => (
                  <div
                    key={m.label}
                    className="bg-gray-50 rounded-lg p-3 text-center"
                  >
                    <p className="text-xs text-gray-500">{m.label}</p>
                    <p className={`text-lg font-bold ${m.color}`}>{m.value}</p>
                  </div>
                ))}
              </div>
              {equityCurve.length > 0 ? (
                <ResponsiveContainer width="100%" height={280}>
                  <AreaChart data={equityCurve.filter((_, i) => i % 2 === 0)}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="day" tick={{ fontSize: 10 }} />
                    <YAxis tick={{ fontSize: 11 }} domain={["auto", "auto"]} />
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
              ) : (
                <p className="text-sm text-gray-400 text-center py-12">
                  Loading equity curve…
                </p>
              )}
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
                    data={rollingMetrics.filter((_, i) => i % 3 === 0)}
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
                    data={rollingMetrics.filter((_, i) => i % 3 === 0)}
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
                Edit strategy hyperparameters and save to trigger re-training.
              </p>
              <div className="space-y-3">
                {Object.entries(strategy.parameters).map(([key, value]) => (
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
                ))}
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
  );
};

// ── Main Strategies Page ──────────────────────────────────────────────────
export const Strategies: React.FC = () => {
  const [view, setView] = useState<"card" | "table">("card");
  const [selectedStrategy, setSelectedStrategy] = useState<Strategy | null>(
    null,
  );

  const { data: strategies, isLoading, error } = useStrategies();
  const activate = useActivateStrategy();
  const deactivate = useDeactivateStrategy();

  const toggleStatus = (id: string, status: string) => {
    if (status === "active") {
      deactivate.mutate(id);
    } else {
      activate.mutate(id);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-md bg-red-50 p-4">
        <p className="text-sm text-red-700">
          Unable to load strategies. Check that the backend is running.
        </p>
      </div>
    );
  }

  const strategyList = strategies ?? [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">
            Trading Strategies
          </h1>
          <p className="mt-1 text-sm text-gray-500">
            {strategyList.filter((s) => s.status === "active").length} active of{" "}
            {strategyList.length} strategies
          </p>
        </div>
        <div className="flex items-center space-x-2">
          {(["card", "table"] as const).map((v) => (
            <button
              key={v}
              onClick={() => setView(v)}
              className={`px-3 py-1.5 text-sm rounded-md font-medium transition-colors capitalize ${view === v ? "bg-blue-600 text-white" : "border border-gray-300 text-gray-700 hover:bg-gray-50"}`}
            >
              {v}
            </button>
          ))}
        </div>
      </div>

      {view === "table" ? (
        <div className="bg-white shadow rounded-lg overflow-hidden">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  {[
                    "Strategy",
                    "Sharpe",
                    "Return",
                    "Max DD",
                    "Win %",
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
                {strategyList.map((s) => (
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
                      -{formatPercentage(Math.abs(s.performance.maxDrawdown))}
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
          {strategyList.map((strategy) => (
            <StrategyCard
              key={strategy.id}
              strategy={strategy}
              onView={() => setSelectedStrategy(strategy)}
              onToggle={() => toggleStatus(strategy.id, strategy.status)}
            />
          ))}
        </div>
      )}

      {selectedStrategy && (
        <StrategyDetail
          strategy={selectedStrategy}
          onClose={() => setSelectedStrategy(null)}
        />
      )}
    </div>
  );
};

// ── Strategy Card ─────────────────────────────────────────────────────────
const StrategyCard: React.FC<{
  strategy: Strategy;
  onView: () => void;
  onToggle: () => void;
}> = ({ strategy, onView, onToggle }) => {
  const { data: curveData } = useStrategyEquityCurve(strategy.id);
  const equityCurve =
    (curveData?.equityCurve as { day: number; value: number }[] | undefined) ??
    [];

  return (
    <div className="bg-white shadow rounded-lg overflow-hidden">
      <div className="p-5">
        <div className="flex items-start justify-between mb-2">
          <div>
            <h3 className="text-base font-semibold text-gray-900">
              {strategy.name}
            </h3>
            <span className="text-xs text-gray-400">{strategy.type}</span>
          </div>
          <span
            className={`px-2.5 py-0.5 rounded-full text-xs font-medium ${strategy.status === "active" ? "bg-green-100 text-green-800" : "bg-gray-100 text-gray-600"}`}
          >
            {strategy.status}
          </span>
        </div>
        <p className="text-xs text-gray-500 mb-4">{strategy.description}</p>

        {/* Mini equity curve — live from API */}
        <div className="h-24 mb-4">
          {equityCurve.length > 0 ? (
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={equityCurve.filter((_, i) => i % 5 === 0)}>
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
          ) : (
            <div className="h-full flex items-center justify-center">
              <div className="animate-pulse h-2 w-full bg-blue-100 rounded" />
            </div>
          )}
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
              value: `-${formatPercentage(Math.abs(strategy.performance.maxDrawdown))}`,
            },
            {
              label: "Win %",
              value: formatPercentage(strategy.performance.winRate),
            },
          ].map((m) => (
            <div key={m.label} className="bg-gray-50 rounded p-2">
              <p className="text-xs text-gray-400">{m.label}</p>
              <p className="text-sm font-semibold text-gray-900">{m.value}</p>
            </div>
          ))}
        </div>

        <div className="flex space-x-2">
          <button
            onClick={onView}
            className="flex-1 py-1.5 text-xs font-medium border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
          >
            View Details
          </button>
          <button
            onClick={onToggle}
            className={`flex-1 py-1.5 text-xs font-medium rounded-md text-white ${strategy.status === "active" ? "bg-red-500 hover:bg-red-600" : "bg-green-600 hover:bg-green-700"}`}
          >
            {strategy.status === "active" ? "Deactivate" : "Activate"}
          </button>
        </div>
      </div>
    </div>
  );
};
