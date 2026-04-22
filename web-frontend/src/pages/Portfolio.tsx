import type React from "react";
import { useState } from "react";
import {
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
import {
  usePortfolio,
  usePositions,
  useClosePosition,
} from "../hooks/usePortfolio";
import { usePortfolioPerformance } from "../hooks/usePortfolioPerformance";
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

const LABEL = ({
  cx,
  cy,
  midAngle,
  innerRadius,
  outerRadius,
  percent,
}: PieLabelRenderProps) => {
  if (
    !cx ||
    !cy ||
    !midAngle ||
    !innerRadius ||
    !outerRadius ||
    !percent ||
    Number(percent) < 0.05
  )
    return null;
  const RADIAN = Math.PI / 180;
  const radius =
    Number(innerRadius) + (Number(outerRadius) - Number(innerRadius)) * 0.5;
  const x = Number(cx) + radius * Math.cos(-Number(midAngle) * RADIAN);
  const y = Number(cy) + radius * Math.sin(-Number(midAngle) * RADIAN);
  return (
    <text
      x={x}
      y={y}
      fill="white"
      textAnchor="middle"
      dominantBaseline="central"
      fontSize={11}
      fontWeight={600}
    >
      {`${(Number(percent) * 100).toFixed(0)}%`}
    </text>
  );
};

export const Portfolio: React.FC = () => {
  const [timeframe, setTimeframe] = useState("1M");
  const { data: portfolio, isLoading: portfolioLoading } = usePortfolio();
  const { data: positions, isLoading: positionsLoading } = usePositions();
  const { data: performance, isLoading: perfLoading } =
    usePortfolioPerformance(timeframe);
  const closePosition = useClosePosition();

  if (portfolioLoading || positionsLoading || perfLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600" />
      </div>
    );
  }

  if (!portfolio) {
    return (
      <div className="rounded-md bg-red-50 p-4">
        <p className="text-sm text-red-700">
          Unable to load portfolio. Check that the backend is running.
        </p>
      </div>
    );
  }

  const openPositions = positions ?? [];
  const allocation = portfolio.allocation ?? [];
  const perfData = performance as
    | {
        equityCurve: { timestamp: string; value: number }[];
        metrics: Record<string, number>;
      }
    | undefined;
  const metrics = perfData?.metrics;

  const sectorData = openPositions.reduce<Record<string, number>>((acc, p) => {
    const sector = (p as { sector?: string }).sector ?? "Other";
    acc[sector] = (acc[sector] ?? 0) + p.currentPrice * p.quantity;
    return acc;
  }, {});
  const sectorChartData = Object.entries(sectorData).map(([name, value]) => ({
    name,
    value: Math.round(value),
  }));

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Portfolio</h1>
        <p className="mt-1 text-sm text-gray-500">
          Holdings, allocation, and attribution
        </p>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        {[
          {
            label: "Total Value",
            value: formatCurrency(portfolio.totalValue),
            color: "text-gray-900",
          },
          {
            label: "Cash",
            value: formatCurrency(portfolio.cash),
            color: "text-gray-900",
          },
          {
            label: "Daily P&L",
            value: formatCurrency(portfolio.dailyPnL),
            color: getColorForValue(portfolio.dailyPnL),
          },
          {
            label: "Total P&L",
            value: formatCurrency(portfolio.totalPnL),
            color: getColorForValue(portfolio.totalPnL),
          },
        ].map(({ label, value, color }) => (
          <div key={label} className="bg-white shadow rounded-lg p-4">
            <p className="text-xs text-gray-500">{label}</p>
            <p className={`text-xl font-bold mt-1 ${color}`}>{value}</p>
          </div>
        ))}
      </div>

      {/* Performance metrics */}
      {metrics && (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          {[
            { label: "Sharpe Ratio", value: metrics.sharpeRatio?.toFixed(2) },
            {
              label: "Max Drawdown",
              value: `${(metrics.maxDrawdown * 100).toFixed(1)}%`,
            },
            {
              label: "Ann. Return",
              value: formatPercentage(metrics.annualisedReturn),
            },
            {
              label: "Volatility",
              value: formatPercentage(metrics.volatility),
            },
          ].map(({ label, value }) => (
            <div key={label} className="bg-white shadow rounded-lg p-4">
              <p className="text-xs text-gray-500">{label}</p>
              <p className="text-xl font-bold text-blue-700 mt-1">{value}</p>
            </div>
          ))}
        </div>
      )}

      {/* Charts row */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Allocation pie */}
        <div className="bg-white shadow rounded-lg p-6">
          <h2 className="text-base font-semibold text-gray-900 mb-4">
            Allocation by Asset
          </h2>
          {allocation.length > 0 ? (
            <ResponsiveContainer width="100%" height={260}>
              <PieChart>
                <Pie
                  data={allocation}
                  cx="50%"
                  cy="50%"
                  outerRadius={100}
                  dataKey="value"
                  nameKey="ticker"
                  labelLine={false}
                  label={LABEL}
                >
                  {allocation.map((_, i) => (
                    <Cell key={i} fill={COLORS[i % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip
                  formatter={(v) => [formatCurrency(Number(v)), "Value"]}
                />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-sm text-gray-400 text-center py-12">
              No allocation data.
            </p>
          )}
        </div>

        {/* Sector bar */}
        <div className="bg-white shadow rounded-lg p-6">
          <h2 className="text-base font-semibold text-gray-900 mb-4">
            Allocation by Sector
          </h2>
          {sectorChartData.length > 0 ? (
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={sectorChartData} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                <XAxis
                  type="number"
                  tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`}
                  tick={{ fontSize: 11 }}
                />
                <YAxis
                  dataKey="name"
                  type="category"
                  width={120}
                  tick={{ fontSize: 11 }}
                />
                <Tooltip
                  formatter={(v) => [formatCurrency(Number(v)), "Value"]}
                />
                <Bar dataKey="value" radius={[0, 4, 4, 0]}>
                  {sectorChartData.map((_, i) => (
                    <Cell key={i} fill={COLORS[i % COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-sm text-gray-400 text-center py-12">
              No sector data.
            </p>
          )}
        </div>
      </div>

      {/* Timeframe selector */}
      <div className="flex items-center space-x-2">
        <span className="text-sm text-gray-500">Timeframe:</span>
        {["1W", "1M", "3M", "6M", "1Y"].map((t) => (
          <button
            key={t}
            onClick={() => setTimeframe(t)}
            className={`px-3 py-1 text-xs rounded-md font-medium transition-colors ${timeframe === t ? "bg-blue-600 text-white" : "border border-gray-300 text-gray-600 hover:bg-gray-50"}`}
          >
            {t}
          </button>
        ))}
      </div>

      {/* Positions table */}
      <div className="bg-white shadow rounded-lg overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-base font-semibold text-gray-900">
            Open Positions ({openPositions.length})
          </h2>
        </div>
        {openPositions.length === 0 ? (
          <p className="px-6 py-8 text-sm text-gray-400">No open positions.</p>
        ) : (
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
                    "Unrealised P&L",
                    "Weight",
                    "Beta",
                    "VaR 95%",
                    "",
                  ].map((h) => (
                    <th
                      key={h}
                      className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider last:text-right"
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {openPositions.map((pos) => {
                  const p = pos as typeof pos & {
                    sector?: string;
                    weight?: number;
                    beta?: number;
                    var95?: number;
                  };
                  return (
                    <tr key={pos.id} className="hover:bg-gray-50">
                      <td className="px-4 py-3 font-medium text-gray-900">
                        {pos.ticker}
                      </td>
                      <td className="px-4 py-3 text-gray-500">
                        {p.sector ?? "—"}
                      </td>
                      <td className="px-4 py-3 text-gray-500">
                        {pos.quantity}
                      </td>
                      <td className="px-4 py-3 text-gray-500">
                        {formatCurrency(pos.entryPrice)}
                      </td>
                      <td className="px-4 py-3 text-gray-500">
                        {formatCurrency(pos.currentPrice)}
                      </td>
                      <td
                        className={`px-4 py-3 font-medium ${getColorForValue(pos.unrealizedPnL)}`}
                      >
                        {formatCurrency(pos.unrealizedPnL)}
                      </td>
                      <td className="px-4 py-3 text-gray-500">
                        {p.weight ? `${(p.weight * 100).toFixed(1)}%` : "—"}
                      </td>
                      <td className="px-4 py-3 text-gray-500">
                        {p.beta?.toFixed(2) ?? "—"}
                      </td>
                      <td className="px-4 py-3 text-gray-500">
                        {p.var95 ? formatCurrency(p.var95) : "—"}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <button
                          onClick={() => closePosition.mutate(pos.id)}
                          disabled={closePosition.isPending}
                          className="text-red-600 hover:text-red-900 text-xs focus:outline-none disabled:opacity-40"
                        >
                          Close
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
