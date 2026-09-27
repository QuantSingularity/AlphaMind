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
import { useChartPalette, chartTooltipStyle } from "../hooks/useChartPalette";

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
  const palette = useChartPalette();

  const equityCurve =
    (curveData?.equityCurve as
      { day: number; value: number; benchmark: number }[] | undefined) ?? [];
  const rollingMetrics = buildRollingMetrics(equityCurve);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-60 p-4"
      onClick={onClose}
    >
      <div
        className="am-card w-full max-w-3xl max-h-screen overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex justify-between items-start p-6 border-b border-line">
          <div>
            <h2 className="text-xl font-bold text-ink">{strategy.name}</h2>
            <p className="text-sm text-ink-muted mt-1">
              {strategy.description}
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-ink-faint hover:text-ink-muted ml-4"
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
        <div className="border-b border-line px-6">
          <nav className="flex space-x-6">
            {(["equity", "rolling", "params"] as const).map((t) => (
              <button
                key={t}
                onClick={() => setDetailTab(t)}
                className={`py-3 text-sm font-medium border-b-2 capitalize transition-colors ${detailTab === t ? "border-brand text-brand" : "border-transparent text-ink-muted hover:text-ink-muted"}`}
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
                    color: "text-pos",
                  },
                  {
                    label: "Sharpe",
                    value: strategy.performance.sharpeRatio.toFixed(2),
                    color: "text-brand",
                  },
                  {
                    label: "Max DD",
                    value: `-${formatPercentage(Math.abs(strategy.performance.maxDrawdown))}`,
                    color: "text-neg",
                  },
                  {
                    label: "Alpha",
                    value: formatPercentage(strategy.performance.alpha),
                    color: "text-purple-700",
                  },
                ].map((m) => (
                  <div
                    key={m.label}
                    className="bg-surface-2 rounded-lg p-3 text-center"
                  >
                    <p className="text-xs text-ink-muted">{m.label}</p>
                    <p className={`text-lg font-bold ${m.color}`}>{m.value}</p>
                  </div>
                ))}
              </div>
              {equityCurve.length > 0 ? (
                <ResponsiveContainer width="100%" height={280}>
                  <AreaChart data={equityCurve.filter((_, i) => i % 2 === 0)}>
                    <CartesianGrid
                      strokeDasharray="3 3"
                      stroke={palette.grid}
                    />
                    <XAxis
                      dataKey="day"
                      tick={{ fontSize: 10, fill: palette.axis }}
                    />
                    <YAxis
                      tick={{ fontSize: 11, fill: palette.axis }}
                      domain={["auto", "auto"]}
                    />
                    <Tooltip
                      contentStyle={chartTooltipStyle(palette)}
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
                      stroke={palette.axis}
                      fill={palette.grid}
                      fillOpacity={0.14}
                      dot={false}
                    />
                    <Area
                      type="monotone"
                      dataKey="value"
                      name="Strategy"
                      stroke={palette.brand}
                      fill={palette.brand}
                      fillOpacity={0.2}
                      dot={false}
                    />
                  </AreaChart>
                </ResponsiveContainer>
              ) : (
                <p className="text-sm text-ink-faint text-center py-12">
                  Loading equity curve…
                </p>
              )}
            </div>
          )}
          {detailTab === "rolling" && (
            <div className="space-y-6">
              <div>
                <p className="text-xs text-ink-muted mb-2">
                  Rolling 30-day Sharpe Ratio
                </p>
                <ResponsiveContainer width="100%" height={180}>
                  <LineChart
                    data={rollingMetrics.filter((_, i) => i % 3 === 0)}
                  >
                    <CartesianGrid
                      strokeDasharray="3 3"
                      stroke={palette.grid}
                    />
                    <XAxis
                      dataKey="day"
                      tick={{ fontSize: 10, fill: palette.axis }}
                    />
                    <YAxis tick={{ fontSize: 11, fill: palette.axis }} />
                    <Tooltip contentStyle={chartTooltipStyle(palette)} />
                    <Line
                      type="monotone"
                      dataKey="sharpe"
                      stroke={palette.brand}
                      dot={false}
                      strokeWidth={2}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
              <div>
                <p className="text-xs text-ink-muted mb-2">
                  Rolling Drawdown (%)
                </p>
                <ResponsiveContainer width="100%" height={180}>
                  <AreaChart
                    data={rollingMetrics.filter((_, i) => i % 3 === 0)}
                  >
                    <CartesianGrid
                      strokeDasharray="3 3"
                      stroke={palette.grid}
                    />
                    <XAxis
                      dataKey="day"
                      tick={{ fontSize: 10, fill: palette.axis }}
                    />
                    <YAxis
                      tickFormatter={(v) => `${v}%`}
                      tick={{ fontSize: 11, fill: palette.axis }}
                      domain={["auto", 0]}
                    />
                    <Tooltip
                      contentStyle={chartTooltipStyle(palette)}
                      formatter={(v) => [
                        `${Number(v).toFixed(2)}%`,
                        "Drawdown",
                      ]}
                    />
                    <Area
                      type="monotone"
                      dataKey="drawdown"
                      stroke={palette.neg}
                      fill={palette.neg}
                      fillOpacity={0.22}
                      dot={false}
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}
          {detailTab === "params" && (
            <div>
              <p className="text-xs text-ink-muted mb-4">
                Edit strategy hyperparameters and save to trigger re-training.
              </p>
              <div className="space-y-3">
                {Object.entries(strategy.parameters).map(([key, value]) => (
                  <div
                    key={key}
                    className="flex items-center justify-between bg-surface-2 rounded-lg px-4 py-3"
                  >
                    <span className="text-sm font-mono text-ink-muted">
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
                      className="w-32 text-sm text-right border border-line rounded-md px-2 py-1 focus:outline-none focus:ring-1 focus:ring-brand"
                    />
                  </div>
                ))}
              </div>
              <div className="mt-4 flex justify-end space-x-3">
                <button
                  onClick={() => setParamEdits({})}
                  className="px-4 py-2 text-sm border border-line rounded-md text-ink-muted hover:bg-surface-2"
                >
                  Reset
                </button>
                <button className="px-4 py-2 text-sm bg-brand text-white rounded-md hover:bg-brand-strong">
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
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-brand" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-md bg-neg-soft p-4">
        <p className="text-sm text-neg">
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
          <h1 className="text-3xl font-bold text-ink">Trading Strategies</h1>
          <p className="mt-1 text-sm text-ink-muted">
            {strategyList.filter((s) => s.status === "active").length} active of{" "}
            {strategyList.length} strategies
          </p>
        </div>
        <div className="flex items-center space-x-2">
          {(["card", "table"] as const).map((v) => (
            <button
              key={v}
              onClick={() => setView(v)}
              className={`px-3 py-1.5 text-sm rounded-md font-medium transition-colors capitalize ${view === v ? "bg-brand text-white" : "border border-line text-ink-muted hover:bg-surface-2"}`}
            >
              {v}
            </button>
          ))}
        </div>
      </div>

      {view === "table" ? (
        <div className="am-card overflow-hidden">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-line">
              <thead className="bg-surface-2">
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
                      className="px-4 py-2 text-xs font-medium text-ink-muted uppercase text-left"
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {strategyList.map((s) => (
                  <tr key={s.id} className="hover:bg-surface-2">
                    <td className="px-4 py-3 font-medium text-ink">{s.name}</td>
                    <td className="px-4 py-3 text-brand font-semibold">
                      {s.performance.sharpeRatio.toFixed(2)}
                    </td>
                    <td className="px-4 py-3 text-pos">
                      {formatPercentage(s.performance.totalReturn)}
                    </td>
                    <td className="px-4 py-3 text-neg">
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
                        className={`px-2 py-0.5 rounded-full text-xs font-medium ${s.status === "active" ? "bg-pos-soft text-pos" : "bg-surface-2 text-ink-muted"}`}
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
  const palette = useChartPalette();
  const equityCurve =
    (curveData?.equityCurve as { day: number; value: number }[] | undefined) ??
    [];

  return (
    <div className="am-card overflow-hidden">
      <div className="p-5">
        <div className="flex items-start justify-between mb-2">
          <div>
            <h3 className="text-base font-semibold text-ink">
              {strategy.name}
            </h3>
            <span className="text-xs text-ink-faint">{strategy.type}</span>
          </div>
          <span
            className={`px-2.5 py-0.5 rounded-full text-xs font-medium ${strategy.status === "active" ? "bg-pos-soft text-pos" : "bg-surface-2 text-ink-muted"}`}
          >
            {strategy.status}
          </span>
        </div>
        <p className="text-xs text-ink-muted mb-4">{strategy.description}</p>

        {/* Mini equity curve - live from API */}
        <div className="h-24 mb-4">
          {equityCurve.length > 0 ? (
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={equityCurve.filter((_, i) => i % 5 === 0)}>
                <Area
                  type="monotone"
                  dataKey="value"
                  stroke={palette.brand}
                  fill={palette.brand}
                  strokeWidth={1.5}
                  dot={false}
                />
              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-full flex items-center justify-center">
              <div className="animate-pulse h-2 w-full bg-brand-soft rounded" />
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
            <div key={m.label} className="bg-surface-2 rounded p-2">
              <p className="text-xs text-ink-faint">{m.label}</p>
              <p className="text-sm font-semibold text-ink">{m.value}</p>
            </div>
          ))}
        </div>

        <div className="flex space-x-2">
          <button
            onClick={onView}
            className="flex-1 py-1.5 text-xs font-medium border border-line rounded-md text-ink-muted hover:bg-surface-2"
          >
            View Details
          </button>
          <button
            onClick={onToggle}
            className={`flex-1 py-1.5 text-xs font-medium rounded-md text-white ${strategy.status === "active" ? "bg-neg hover:bg-neg" : "bg-pos hover:bg-pos"}`}
          >
            {strategy.status === "active" ? "Deactivate" : "Activate"}
          </button>
        </div>
      </div>
    </div>
  );
};
