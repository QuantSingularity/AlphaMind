import type React from "react";
import { useState } from "react";
import {
  Area,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ComposedChart,
  Legend,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { formatCurrency, formatPercentage } from "../utils/format";
import { useStrategies } from "../hooks/useStrategies";
import { useRunBacktest } from "../hooks/useBacktest";
import type { BacktestResult } from "../types";

interface BacktestConfig {
  strategyId: string;
  startDate: string;
  endDate: string;
  initialCapital: number;
  benchmark: string;
  transactionCost: number;
  slippage: number;
}

const DEFAULT_CONFIG: BacktestConfig = {
  strategyId: "",
  startDate: "2019-01-01",
  endDate: "2023-12-31",
  initialCapital: 100_000,
  benchmark: "SPY",
  transactionCost: 0.0005,
  slippage: 0.0002,
};

export const Backtest: React.FC = () => {
  const [config, setConfig] = useState<BacktestConfig>(DEFAULT_CONFIG);
  const [result, setResult] = useState<
    (BacktestResult & { equityCurve?: unknown[] }) | null
  >(null);

  const { data: strategies, isLoading: strategiesLoading } = useStrategies();
  const runBacktest = useRunBacktest();

  const handleRun = async () => {
    if (!config.strategyId) return;
    const res = await runBacktest.mutateAsync({
      strategyId: config.strategyId,
      startDate: config.startDate,
      endDate: config.endDate,
      initialCapital: config.initialCapital,
    });
    setResult(res as BacktestResult & { equityCurve?: Array<unknown> });
  };

  const equityCurve =
    (result?.equityCurve as
      | { date: string; equity: number; benchmark: number; drawdown: number }[]
      | undefined) ?? [];
  const monthlyReturns =
    equityCurve.length > 0
      ? equityCurve
          .filter((_, i) => i % 21 === 0)
          .map((pt, i) => ({
            month: `M${i + 1}`,
            return:
              i === 0
                ? 0
                : parseFloat(
                    (
                      (pt.equity /
                        equityCurve[Math.max(0, i * 21 - 21)].equity -
                        1) *
                      100
                    ).toFixed(2),
                  ),
          }))
      : [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Backtesting</h1>
        <p className="mt-1 text-sm text-gray-500">
          Run walk-forward out-of-sample backtests on your strategies
        </p>
      </div>

      {/* Config Panel */}
      <div className="bg-white shadow rounded-lg p-6">
        <h2 className="text-base font-semibold text-gray-900 mb-4">
          Backtest Configuration
        </h2>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">
              Strategy
            </label>
            <select
              value={config.strategyId}
              onChange={(e) =>
                setConfig({ ...config, strategyId: e.target.value })
              }
              className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
            >
              <option value="">Select a strategy…</option>
              {(strategies ?? []).map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">
              Start Date
            </label>
            <input
              type="date"
              value={config.startDate}
              onChange={(e) =>
                setConfig({ ...config, startDate: e.target.value })
              }
              className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">
              End Date
            </label>
            <input
              type="date"
              value={config.endDate}
              onChange={(e) =>
                setConfig({ ...config, endDate: e.target.value })
              }
              className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">
              Initial Capital ($)
            </label>
            <input
              type="number"
              value={config.initialCapital}
              onChange={(e) =>
                setConfig({ ...config, initialCapital: Number(e.target.value) })
              }
              className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">
              Transaction Cost (bps)
            </label>
            <input
              type="number"
              step="0.0001"
              value={config.transactionCost}
              onChange={(e) =>
                setConfig({
                  ...config,
                  transactionCost: Number(e.target.value),
                })
              }
              className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">
              Slippage (bps)
            </label>
            <input
              type="number"
              step="0.0001"
              value={config.slippage}
              onChange={(e) =>
                setConfig({ ...config, slippage: Number(e.target.value) })
              }
              className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>
        </div>
        <div className="mt-4 flex items-center space-x-3">
          <button
            onClick={handleRun}
            disabled={
              !config.strategyId || runBacktest.isPending || strategiesLoading
            }
            className="px-6 py-2 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed flex items-center space-x-2"
          >
            {runBacktest.isPending && (
              <span className="animate-spin h-4 w-4 border-2 border-white border-t-transparent rounded-full" />
            )}
            <span>{runBacktest.isPending ? "Running…" : "Run Backtest"}</span>
          </button>
          {result && (
            <span className="text-xs text-green-600 font-medium">
              ✓ Backtest complete
            </span>
          )}
        </div>
        {runBacktest.isError && (
          <p className="mt-2 text-xs text-red-600">
            Backtest failed. Check that the backend is running and a strategy is
            selected.
          </p>
        )}
      </div>

      {/* Results */}
      {result && (
        <div className="space-y-6">
          {/* Summary metrics */}
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4 lg:grid-cols-6">
            {[
              {
                label: "Total Return",
                value: formatPercentage(result.totalReturn),
              },
              {
                label: "Ann. Return",
                value: formatPercentage(
                  (result as { annualisedReturn?: number }).annualisedReturn ??
                    0,
                ),
              },
              {
                label: "Sharpe",
                value: (
                  (result as { sharpeRatio?: number }).sharpeRatio ?? 0
                ).toFixed(2),
              },
              {
                label: "Sortino",
                value: (
                  (result as { sortinoRatio?: number }).sortinoRatio ?? 0
                ).toFixed(2),
              },
              {
                label: "Max DD",
                value: formatPercentage(
                  Math.abs(
                    (result as { maxDrawdown?: number }).maxDrawdown ?? 0,
                  ),
                ),
              },
              {
                label: "Win Rate",
                value: formatPercentage(
                  (result as { winRate?: number }).winRate ?? 0,
                ),
              },
              {
                label: "Final Capital",
                value: formatCurrency(result.finalCapital),
              },
              {
                label: "Profit Factor",
                value: (
                  (result as { profitFactor?: number }).profitFactor ?? 0
                ).toFixed(2),
              },
            ].map(({ label, value }) => (
              <div key={label} className="bg-white shadow rounded-lg p-4">
                <p className="text-xs text-gray-500">{label}</p>
                <p className="text-lg font-bold text-gray-900 mt-1">{value}</p>
              </div>
            ))}
          </div>

          {/* Equity curve */}
          {equityCurve.length > 0 && (
            <div className="bg-white shadow rounded-lg p-6">
              <h2 className="text-base font-semibold text-gray-900 mb-4">
                Equity Curve vs Benchmark
              </h2>
              <ResponsiveContainer width="100%" height={320}>
                <ComposedChart data={equityCurve.filter((_, i) => i % 2 === 0)}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" tick={{ fontSize: 10 }} />
                  <YAxis
                    yAxisId="left"
                    tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`}
                    tick={{ fontSize: 11 }}
                  />
                  <YAxis
                    yAxisId="right"
                    orientation="right"
                    tickFormatter={(v) => `${v}%`}
                    tick={{ fontSize: 11 }}
                    domain={["auto", 0]}
                  />
                  <Tooltip
                    formatter={(v, n) =>
                      n === "drawdown"
                        ? [`${Number(v).toFixed(2)}%`, "Drawdown"]
                        : [
                            formatCurrency(Number(v)),
                            n === "equity" ? "Strategy" : "Benchmark",
                          ]
                    }
                  />
                  <Legend />
                  <Area
                    yAxisId="left"
                    type="monotone"
                    dataKey="benchmark"
                    name="Benchmark"
                    stroke="#9ca3af"
                    fill="#f3f4f6"
                    fillOpacity={0.4}
                    dot={false}
                  />
                  <Area
                    yAxisId="left"
                    type="monotone"
                    dataKey="equity"
                    name="Strategy"
                    stroke="#2563eb"
                    fill="#eff6ff"
                    fillOpacity={0.6}
                    dot={false}
                  />
                  <Area
                    yAxisId="right"
                    type="monotone"
                    dataKey="drawdown"
                    name="Drawdown %"
                    stroke="#ef4444"
                    fill="#fee2e2"
                    fillOpacity={0.5}
                    dot={false}
                  />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* Monthly returns */}
          {monthlyReturns.length > 0 && (
            <div className="bg-white shadow rounded-lg p-6">
              <h2 className="text-base font-semibold text-gray-900 mb-4">
                Monthly Returns (%)
              </h2>
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={monthlyReturns}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="month" tick={{ fontSize: 11 }} />
                  <YAxis
                    tickFormatter={(v) => `${v}%`}
                    tick={{ fontSize: 11 }}
                  />
                  <Tooltip
                    formatter={(v) => [`${Number(v).toFixed(2)}%`, "Return"]}
                  />
                  <ReferenceLine y={0} stroke="#6b7280" strokeWidth={1} />
                  <Bar dataKey="return" radius={[3, 3, 0, 0]}>
                    {monthlyReturns.map((m, i) => (
                      <Cell
                        key={i}
                        fill={m.return >= 0 ? "#10b981" : "#ef4444"}
                      />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
