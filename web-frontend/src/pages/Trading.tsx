import { useState } from "react";
import type React from "react";
import { useCancelOrder, useCreateOrder, useOrders } from "../hooks/useTrading";
import {
  Badge,
  EmptyState,
  ErrorState,
  SectionHeading,
  Spinner,
} from "../components/ui";
import { formatCurrency, formatNumber } from "../utils/format";
import type { Order } from "../types";

type Side = "BUY" | "SELL";
type OrderType = "MARKET" | "LIMIT" | "STOP";

const statusTone = (status: string): "pos" | "neg" | "warn" | "neutral" => {
  switch (status) {
    case "filled":
      return "pos";
    case "rejected":
    case "cancelled":
      return "neg";
    case "pending":
      return "warn";
    default:
      return "neutral";
  }
};

export const Trading: React.FC = () => {
  const { data: orders, isLoading, isError, refetch } = useOrders();
  const createOrder = useCreateOrder();
  const cancelOrder = useCancelOrder();

  const [ticker, setTicker] = useState("");
  const [side, setSide] = useState<Side>("BUY");
  const [quantity, setQuantity] = useState("");
  const [orderType, setOrderType] = useState<OrderType>("MARKET");
  const [price, setPrice] = useState("");
  const [formError, setFormError] = useState<string | null>(null);

  const needsPrice = orderType !== "MARKET";

  const submit = () => {
    setFormError(null);
    const qty = Number(quantity);
    if (!ticker.trim()) return setFormError("Enter a ticker.");
    if (!qty || qty <= 0)
      return setFormError("Enter a quantity greater than zero.");
    if (needsPrice && (!Number(price) || Number(price) <= 0)) {
      return setFormError("Enter a price for limit and stop orders.");
    }

    const payload: Partial<Order> = {
      ticker: ticker.trim().toUpperCase(),
      side,
      quantity: qty,
      orderType,
      ...(needsPrice ? { price: Number(price) } : {}),
    };

    createOrder.mutate(payload, {
      onSuccess: () => {
        setTicker("");
        setQuantity("");
        setPrice("");
      },
    });
  };

  return (
    <div className="space-y-8">
      <SectionHeading
        eyebrow="Execution"
        title="Trading"
        subtitle="Submit orders and monitor the live order blotter."
      />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-5">
        <div className="lg:col-span-2">
          <div className="am-card p-6">
            <h3 className="font-display text-base font-semibold text-ink">
              Order ticket
            </h3>

            <div className="mt-4 space-y-4">
              <label className="block">
                <span className="mb-1.5 block text-sm font-medium text-ink-muted">
                  Ticker
                </span>
                <input
                  className="am-input font-mono uppercase"
                  value={ticker}
                  onChange={(e) => setTicker(e.target.value)}
                  placeholder="AAPL"
                />
              </label>

              <div>
                <span className="mb-1.5 block text-sm font-medium text-ink-muted">
                  Side
                </span>
                <div className="grid grid-cols-2 gap-2">
                  {(["BUY", "SELL"] as Side[]).map((s) => {
                    const active = side === s;
                    const tone =
                      s === "BUY"
                        ? active
                          ? "bg-pos-soft text-pos"
                          : "bg-surface-2 text-ink-muted"
                        : active
                          ? "bg-neg-soft text-neg"
                          : "bg-surface-2 text-ink-muted";
                    return (
                      <button
                        key={s}
                        type="button"
                        onClick={() => setSide(s)}
                        className={`rounded-lg px-4 py-2 text-sm font-semibold transition-colors ${tone}`}
                      >
                        {s}
                      </button>
                    );
                  })}
                </div>
              </div>

              <label className="block">
                <span className="mb-1.5 block text-sm font-medium text-ink-muted">
                  Quantity
                </span>
                <input
                  className="am-input font-mono"
                  value={quantity}
                  onChange={(e) => setQuantity(e.target.value)}
                  inputMode="numeric"
                  placeholder="100"
                />
              </label>

              <label className="block">
                <span className="mb-1.5 block text-sm font-medium text-ink-muted">
                  Order type
                </span>
                <select
                  className="am-input"
                  value={orderType}
                  onChange={(e) => setOrderType(e.target.value as OrderType)}
                >
                  <option value="MARKET">Market</option>
                  <option value="LIMIT">Limit</option>
                  <option value="STOP">Stop</option>
                </select>
              </label>

              {needsPrice && (
                <label className="block">
                  <span className="mb-1.5 block text-sm font-medium text-ink-muted">
                    {orderType === "LIMIT" ? "Limit price" : "Stop price"}
                  </span>
                  <input
                    className="am-input font-mono"
                    value={price}
                    onChange={(e) => setPrice(e.target.value)}
                    inputMode="decimal"
                    placeholder="0.00"
                  />
                </label>
              )}

              {formError && <p className="text-sm text-neg">{formError}</p>}
              {createOrder.isError && (
                <p className="text-sm text-neg">
                  The order could not be submitted. Check the API connection.
                </p>
              )}

              <button
                type="button"
                onClick={submit}
                disabled={createOrder.isPending}
                className={`am-btn w-full ${side === "SELL" ? "border border-neg/50 text-neg hover:bg-neg-soft" : "am-btn-primary"}`}
              >
                {createOrder.isPending
                  ? "Submitting..."
                  : `Submit ${side.toLowerCase()} order`}
              </button>
            </div>
          </div>
        </div>

        <div className="lg:col-span-3">
          <div className="am-card overflow-hidden">
            <div className="flex items-center justify-between border-b border-line px-5 py-4">
              <h3 className="font-display text-base font-semibold text-ink">
                Order blotter
              </h3>
              {orders && (
                <span className="text-sm text-ink-muted">
                  {orders.length} orders
                </span>
              )}
            </div>

            {isLoading && (
              <div className="flex justify-center py-16">
                <Spinner />
              </div>
            )}

            {isError && (
              <div className="p-6">
                <ErrorState
                  message="We could not load orders."
                  onRetry={() => refetch()}
                />
              </div>
            )}

            {!isLoading && !isError && (orders?.length ?? 0) === 0 && (
              <div className="p-6">
                <EmptyState
                  title="No orders yet"
                  hint="Submitted orders will appear here with their status."
                />
              </div>
            )}

            {!isLoading && !isError && (orders?.length ?? 0) > 0 && (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-line text-left text-xs uppercase tracking-wide text-ink-faint">
                      <th className="px-4 py-3 font-medium">Ticker</th>
                      <th className="px-4 py-3 font-medium">Side</th>
                      <th className="px-4 py-3 text-right font-medium">Qty</th>
                      <th className="px-4 py-3 font-medium">Type</th>
                      <th className="px-4 py-3 text-right font-medium">
                        Price
                      </th>
                      <th className="px-4 py-3 font-medium">Status</th>
                      <th className="px-4 py-3 text-right font-medium">
                        Action
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {orders!.map((o) => (
                      <tr key={o.id} className="border-b border-line">
                        <td className="px-4 py-3 font-mono font-semibold text-ink">
                          {o.ticker}
                        </td>
                        <td className="px-4 py-3">
                          <span
                            className={
                              o.side === "BUY" ? "text-pos" : "text-neg"
                            }
                          >
                            {o.side}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-right font-mono tabular-nums text-ink">
                          {formatNumber(o.quantity)}
                        </td>
                        <td className="px-4 py-3 text-ink-muted">
                          {o.orderType}
                        </td>
                        <td className="px-4 py-3 text-right font-mono tabular-nums text-ink-muted">
                          {o.filledPrice
                            ? formatCurrency(o.filledPrice)
                            : o.price
                              ? formatCurrency(o.price)
                              : "-"}
                        </td>
                        <td className="px-4 py-3">
                          <Badge tone={statusTone(o.status)}>{o.status}</Badge>
                        </td>
                        <td className="px-4 py-3 text-right">
                          {o.status === "pending" ? (
                            <button
                              type="button"
                              onClick={() => cancelOrder.mutate(o.id)}
                              disabled={cancelOrder.isPending}
                              className="text-sm font-medium text-neg hover:underline"
                            >
                              Cancel
                            </button>
                          ) : (
                            <span className="text-ink-faint">-</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Trading;
