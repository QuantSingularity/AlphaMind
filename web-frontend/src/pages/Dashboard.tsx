import type React from "react";
import { useCallback } from "react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  usePortfolio,
  usePositions,
  useClosePosition,
} from "../hooks/usePortfolio";
import { usePortfolioPerformance } from "../hooks/usePortfolioPerformance";
import { formatCurrency, getColorForValue } from "../utils/format";

export const Dashboard: React.FC = () => {
  const {
    data: portfolio,
    isLoading: portfolioLoading,
    error: portfolioError,
  } = usePortfolio();
  const { data: positions, isLoading: positionsLoading } = usePositions();
  const { data: performance, isLoading: perfLoading } =
    usePortfolioPerformance("1M");
  const closePosition = useClosePosition();

  const handleClose = useCallback(
    (id: string) => {
      if (confirm("Close this position?")) {
        closePosition.mutate(id);
      }
    },
    [closePosition],
  );

  if (portfolioLoading || positionsLoading || perfLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600" />
      </div>
    );
  }

  if (portfolioError) {
    return (
      <div className="rounded-md bg-red-50 p-4">
        <p className="text-sm text-red-700">
          Unable to load portfolio data. Check that the backend is running.
        </p>
      </div>
    );
  }

  // Use real API data — no hardcoded fallbacks
  const port = portfolio!;
  const openPositions = positions ?? [];
  const equityCurve: { timestamp: string; value: number }[] =
    (
      performance as
        | { equityCurve: { timestamp: string; value: number }[] }
        | undefined
    )?.equityCurve ?? [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Trading Dashboard</h1>
        <p className="mt-1 text-sm text-gray-500">
          Real-time portfolio monitoring and analytics
        </p>
      </div>

      {/* Portfolio Overview Cards */}
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
        {[
          {
            label: "Total Value",
            value: formatCurrency(port.totalValue),
            icon: "M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z",
            colorClass: "text-gray-900",
          },
          {
            label: "Daily P&L",
            value: formatCurrency(port.dailyPnL),
            icon: "M13 7h8m0 0v8m0-8l-8 8-4-4-6 6",
            colorClass: getColorForValue(port.dailyPnL),
          },
          {
            label: "Total P&L",
            value: formatCurrency(port.totalPnL),
            icon: "M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z",
            colorClass: getColorForValue(port.totalPnL),
          },
          {
            label: "Cash",
            value: formatCurrency(port.cash),
            icon: "M17 9V7a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2m2 4h10a2 2 0 002-2v-6a2 2 0 00-2-2H9a2 2 0 00-2 2v6a2 2 0 002 2zm7-5a2 2 0 11-4 0 2 2 0 014 0z",
            colorClass: "text-gray-900",
          },
        ].map(({ label, value, icon, colorClass }) => (
          <div
            key={label}
            className="bg-white overflow-hidden shadow rounded-lg"
          >
            <div className="p-5">
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <svg
                    className="h-6 w-6 text-gray-400"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d={icon}
                    />
                  </svg>
                </div>
                <div className="ml-5 w-0 flex-1">
                  <dl>
                    <dt className="text-sm font-medium text-gray-500 truncate">
                      {label}
                    </dt>
                    <dd className={`text-lg font-semibold ${colorClass}`}>
                      {value}
                    </dd>
                  </dl>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Equity Curve — live from API */}
      <div className="bg-white shadow rounded-lg p-6">
        <h2 className="text-lg font-medium text-gray-900 mb-4">
          Equity Curve (30d)
        </h2>
        {equityCurve.length > 0 ? (
          <ResponsiveContainer width="100%" height={300}>
            <AreaChart data={equityCurve}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="timestamp" tick={{ fontSize: 11 }} />
              <YAxis
                tickFormatter={(v: number) => `$${(v / 1000).toFixed(0)}k`}
              />
              <Tooltip
                formatter={(value: number) => [
                  `$${value.toLocaleString()}`,
                  "Equity",
                ]}
              />
              <Area
                type="monotone"
                dataKey="value"
                stroke="#2563eb"
                fill="#3b82f6"
                fillOpacity={0.3}
              />
            </AreaChart>
          </ResponsiveContainer>
        ) : (
          <p className="text-sm text-gray-400 text-center py-12">
            No performance data available.
          </p>
        )}
      </div>

      {/* Current Positions — live from API */}
      <div className="bg-white shadow rounded-lg overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-medium text-gray-900">
            Open Positions ({openPositions.length})
          </h2>
        </div>
        {openPositions.length === 0 ? (
          <p className="px-6 py-8 text-sm text-gray-400">No open positions.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  {[
                    "Ticker",
                    "Qty",
                    "Entry",
                    "Current",
                    "Unrealised P&L",
                    "",
                  ].map((h) => (
                    <th
                      key={h}
                      className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider last:text-right"
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {openPositions.map((pos) => (
                  <tr
                    key={pos.id}
                    className="hover:bg-gray-50 transition-colors"
                  >
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                      {pos.ticker}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {pos.quantity}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {formatCurrency(pos.entryPrice)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {formatCurrency(pos.currentPrice)}
                    </td>
                    <td
                      className={`px-6 py-4 whitespace-nowrap text-sm font-medium ${getColorForValue(pos.unrealizedPnL)}`}
                    >
                      {formatCurrency(pos.unrealizedPnL)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                      <button className="text-blue-600 hover:text-blue-900 mr-4 focus:outline-none focus:underline">
                        View
                      </button>
                      <button
                        onClick={() => handleClose(pos.id)}
                        disabled={closePosition.isPending}
                        className="text-red-600 hover:text-red-900 focus:outline-none focus:underline disabled:opacity-40"
                      >
                        Close
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
