import type React from "react";
import { useAlternativeDataSources } from "../hooks/useAlternativeData";
import {
  Badge,
  EmptyState,
  ErrorState,
  SectionHeading,
  Spinner,
  StatCard,
} from "../components/ui";
import { formatNumber } from "../utils/format";

const TYPE_LABEL: Record<string, string> = {
  satellite: "Satellite",
  sentiment: "Sentiment",
  sec: "SEC Filings",
  social: "Social / Transactional",
};

const TYPE_ICON: Record<string, string> = {
  satellite: "M12 21a9 9 0 100-18 9 9 0 000 18zm0 0V3m-9 9h18",
  sentiment:
    "M8 10h.01M16 10h.01M9 16s1.5 2 3 2 3-2 3-2M21 12a9 9 0 11-18 0 9 9 0 0118 0z",
  sec: "M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z",
  social:
    "M17 20h5v-2a4 4 0 00-3-3.87M9 20H4v-2a4 4 0 013-3.87m6-1.13a4 4 0 10-4-4 4 4 0 004 4z",
};

const timeAgo = (iso: string): string => {
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return "-";
  const mins = Math.max(0, Math.round((Date.now() - then) / 60000));
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins} min ago`;
  const hrs = Math.round(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.round(hrs / 24)}d ago`;
};

export const AlternativeData: React.FC = () => {
  const {
    data: sources,
    isLoading,
    isError,
    refetch,
  } = useAlternativeDataSources();

  const list = sources ?? [];
  const activeCount = list.filter((s) => s.status === "active").length;
  const totalPoints = list.reduce((sum, s) => sum + (s.dataPoints ?? 0), 0);

  return (
    <div className="space-y-8">
      <SectionHeading
        eyebrow="Signals"
        title="Alternative data"
        subtitle="Non-traditional data feeds processed into tradable signals."
      />

      {isLoading && (
        <div className="flex justify-center py-20">
          <Spinner />
        </div>
      )}

      {isError && (
        <ErrorState
          message="We could not load the alternative data sources."
          onRetry={() => refetch()}
        />
      )}

      {!isLoading && !isError && (
        <>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <StatCard label="Active sources" value={String(activeCount)} />
            <StatCard label="Total sources" value={String(list.length)} />
            <StatCard label="Data points" value={formatNumber(totalPoints)} />
          </div>

          {list.length === 0 ? (
            <EmptyState
              title="No data sources connected"
              hint="Connected feeds will appear here with their status and latency."
            />
          ) : (
            <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
              {list.map((source) => (
                <div key={source.id} className="am-card p-6">
                  <div className="flex items-start gap-4">
                    <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-brand-soft text-brand">
                      <svg
                        className="h-5 w-5"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                        aria-hidden="true"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={1.8}
                          d={TYPE_ICON[source.type] ?? TYPE_ICON.sentiment}
                        />
                      </svg>
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-start justify-between gap-3">
                        <h3 className="font-display text-base font-semibold text-ink">
                          {source.name}
                        </h3>
                        <Badge
                          tone={source.status === "active" ? "pos" : "neutral"}
                        >
                          {source.status}
                        </Badge>
                      </div>
                      <p className="mt-0.5 text-xs font-medium uppercase tracking-wide text-ink-faint">
                        {TYPE_LABEL[source.type] ?? source.type}
                      </p>
                      {source.description && (
                        <p className="mt-2 text-sm leading-relaxed text-ink-muted">
                          {source.description}
                        </p>
                      )}
                      <div className="mt-4 flex flex-wrap gap-x-6 gap-y-2 text-sm">
                        <div>
                          <p className="text-ink-faint">Data points</p>
                          <p className="font-mono tabular-nums text-ink">
                            {formatNumber(source.dataPoints ?? 0)}
                          </p>
                        </div>
                        {source.latency && (
                          <div>
                            <p className="text-ink-faint">Latency</p>
                            <p className="font-mono tabular-nums text-ink">
                              {source.latency}
                            </p>
                          </div>
                        )}
                        <div>
                          <p className="text-ink-faint">Updated</p>
                          <p className="text-ink">
                            {timeAgo(source.lastUpdate)}
                          </p>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default AlternativeData;
