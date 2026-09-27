import { useMemo, useState } from "react";
import type React from "react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { useMarketHistory, useMarketQuotes } from "../hooks/useMarketData";
import { chartTooltipStyle, useChartPalette } from "../hooks/useChartPalette";
import {
  EmptyState,
  ErrorState,
  SectionHeading,
  Spinner,
} from "../components/ui";
import {
  formatCurrency,
  formatNumber,
  getColorForValue,
} from "../utils/format";

export const MarketData: React.FC = () => {
  const { data: quotes, isLoading, isError, refetch } = useMarketQuotes();
  const [selected, setSelected] = useState<string | null>(null);
  const palette = useChartPalette();

  // Default to the first quote without storing it in an effect.
  const effectiveSelected =
    selected ?? (quotes && quotes.length > 0 ? quotes[0].ticker : null);

  const { data: history } = useMarketHistory(effectiveSelected, 90);

  const chartData = useMemo(
    () =>
      (history ?? []).map((bar) => ({
        date: new Date(bar.timestamp).toLocaleDateString(undefined, {
          month: "short",
          day: "numeric",
        }),
        close: bar.close,
      })),
    [history],
  );

  return (
    <div className="space-y-8">
      <SectionHeading
        eyebrow="Markets"
        title="Market data"
        subtitle="Live quotes and price history across the tracked universe."
      />

      {isLoading && (
        <div className="flex justify-center py-20">
          <Spinner />
        </div>
      )}

      {isError && (
        <ErrorState
          message="We could not load market data."
          onRetry={() => refetch()}
        />
      )}

      {!isLoading && !isError && (quotes?.length ?? 0) === 0 && (
        <EmptyState
          title="No quotes available"
          hint="Connected market feeds will appear here."
        />
      )}

      {!isLoading && !isError && (quotes?.length ?? 0) > 0 && (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-5">
          <div className="lg:col-span-3">
            <div className="am-card overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-line text-left text-xs uppercase tracking-wide text-ink-faint">
                      <th className="px-4 py-3 font-medium">Ticker</th>
                      <th className="px-4 py-3 text-right font-medium">Last</th>
                      <th className="px-4 py-3 text-right font-medium">
                        Change
                      </th>
                      <th className="px-4 py-3 text-right font-medium">Bid</th>
                      <th className="px-4 py-3 text-right font-medium">Ask</th>
                      <th className="px-4 py-3 text-right font-medium">
                        Volume
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {quotes!.map((q) => {
                      const change = q.open
                        ? ((q.last - q.open) / q.open) * 100
                        : 0;
                      const active = q.ticker === effectiveSelected;
                      return (
                        <tr
                          key={q.ticker}
                          onClick={() => setSelected(q.ticker)}
                          className={`cursor-pointer border-b border-line transition-colors ${
                            active ? "bg-brand-soft" : "hover:bg-surface-2"
                          }`}
                        >
                          <td className="px-4 py-3 font-mono font-semibold text-ink">
                            {q.ticker}
                          </td>
                          <td className="px-4 py-3 text-right font-mono tabular-nums text-ink">
                            {formatCurrency(q.last)}
                          </td>
                          <td
                            className={`px-4 py-3 text-right font-mono tabular-nums ${getColorForValue(change)}`}
                          >
                            {change >= 0 ? "+" : ""}
                            {change.toFixed(2)}%
                          </td>
                          <td className="px-4 py-3 text-right font-mono tabular-nums text-ink-muted">
                            {formatCurrency(q.bid)}
                          </td>
                          <td className="px-4 py-3 text-right font-mono tabular-nums text-ink-muted">
                            {formatCurrency(q.ask)}
                          </td>
                          <td className="px-4 py-3 text-right font-mono tabular-nums text-ink-muted">
                            {formatNumber(q.volume)}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          </div>

          <div className="lg:col-span-2">
            <div className="am-card p-6">
              <div className="mb-4 flex items-baseline justify-between">
                <h3 className="font-display text-base font-semibold text-ink">
                  {effectiveSelected ?? "-"}
                </h3>
                <span className="text-xs uppercase tracking-wide text-ink-faint">
                  90-day close
                </span>
              </div>
              {chartData.length === 0 ? (
                <div className="flex h-64 items-center justify-center text-sm text-ink-muted">
                  Select a ticker to view price history.
                </div>
              ) : (
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={chartData}>
                      <defs>
                        <linearGradient id="mdFill" x1="0" y1="0" x2="0" y2="1">
                          <stop
                            offset="0%"
                            stopColor={palette.brand}
                            stopOpacity={0.35}
                          />
                          <stop
                            offset="100%"
                            stopColor={palette.brand}
                            stopOpacity={0}
                          />
                        </linearGradient>
                      </defs>
                      <CartesianGrid
                        strokeDasharray="3 3"
                        stroke={palette.grid}
                      />
                      <XAxis
                        dataKey="date"
                        tick={{ fontSize: 10, fill: palette.axis }}
                        stroke={palette.grid}
                        minTickGap={24}
                      />
                      <YAxis
                        tick={{ fontSize: 10, fill: palette.axis }}
                        stroke={palette.grid}
                        domain={["auto", "auto"]}
                        tickFormatter={(v) => `$${Number(v).toFixed(0)}`}
                        width={48}
                      />
                      <Tooltip
                        contentStyle={chartTooltipStyle(palette)}
                        formatter={(v) => [formatCurrency(Number(v)), "Close"]}
                      />
                      <Area
                        type="monotone"
                        dataKey="close"
                        stroke={palette.brand}
                        fill="url(#mdFill)"
                        strokeWidth={2}
                        dot={false}
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default MarketData;
