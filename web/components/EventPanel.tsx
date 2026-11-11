"use client";

import { Icon } from "./Icons";
import { formatYear, localizedEvent } from "@/lib/format";
import {
  HISTORICAL_PERIODS,
  getPeriodForYear,
  getPeriodName,
  getPeriodRange,
  nearestIndexForYear
} from "@/lib/timeline";
import type { Lang, TimelineEntry, UILabels, Variant } from "@/lib/types";

interface EventPanelProps {
  timeline: TimelineEntry[];
  lang: Lang;
  ui: UILabels;
  index: number;
  setIndex: (index: number) => void;
  onClose: () => void;
  variant?: Variant;
}

export default function EventPanel({
  timeline,
  lang,
  ui,
  index,
  setIndex,
  onClose,
  variant = "card"
}: EventPanelProps) {
  const isSheet = variant === "sheet";
  const currentYear = timeline[index]?.year ?? 100;
  const activePeriod = getPeriodForYear(currentYear);

  return (
    <aside
      className={`pointer-events-auto bg-panel panel-shadow ${
        isSheet
          ? "max-h-[44vh] rounded-t-3xl border-b-0 px-4 pb-3.5 pt-2"
          : "max-h-[calc(100dvh-290px)] w-[360px] overflow-hidden rounded-2xl p-4 sm:p-5"
      }`}
    >
      {isSheet ? <div className="mx-auto mb-2 h-1 w-9 rounded-full bg-line-strong/80" /> : null}
      <div className="flex items-start justify-between gap-3 border-b border-line/60 pb-2.5">
        <div className="min-w-0 flex-1">
          <div className="inline-flex items-center gap-1.5 text-[9.5px] font-semibold uppercase tracking-[0.14em] text-accent">
            <span>{ui.period}</span>
            <span className="text-faint">·</span>
            <span>{ui.event}</span>
          </div>
          <h2 className={`mt-0.5 font-semibold leading-tight tracking-[-0.02em] text-ink ${isSheet ? "text-[17px]" : "text-[19px]"}`}>
            {ui.eventsTitle}
          </h2>
          <p className="mt-0.5 text-[10.5px] text-muted">{ui.eventsHint}</p>
        </div>
        <button
          type="button"
          onClick={onClose}
          aria-label={ui.close}
          className="grid size-7 shrink-0 place-items-center rounded-full bg-panel-2/70 text-muted transition hover:bg-control hover:text-ink"
        >
          <Icon name="close" size={17} />
        </button>
      </div>

      <div
        className={`thin-scrollbar mt-2.5 space-y-3.5 overflow-y-auto pr-0.5 ${
          isSheet ? "max-h-[31vh]" : "max-h-[calc(100dvh-395px)]"
        }`}
      >
        {/* major historical eras */}
        <div className="space-y-1">
          <div className="flex items-center justify-between px-2 pb-1">
            <span className="text-[9.5px] font-semibold uppercase tracking-[0.12em] text-muted">
              {ui.historicalPeriods}
            </span>
            <span className="text-[9.5px] font-medium tabular-nums text-muted">
              {HISTORICAL_PERIODS.length} {ui.periodsSuffix}
            </span>
          </div>
          {HISTORICAL_PERIODS.map((period) => {
            const isCurrent = activePeriod.id === period.id;
            const title = getPeriodName(period, lang);
            const range = getPeriodRange(period, lang);
            const targetYear = Math.max(-3500, period.from);
            const targetIdx = nearestIndexForYear(timeline, targetYear);
            const targetEntry = timeline[targetIdx];
            return (
              <button
                key={period.id}
                type="button"
                onClick={() => setIndex(targetIdx)}
                className={`grid w-full grid-cols-[68px_minmax(0,1fr)] items-center gap-2.5 rounded-xl px-2 py-2 text-left transition ${
                  isCurrent
                    ? "bg-tab-active shadow-xs"
                    : "hover:bg-panel-2/80"
                }`}
              >
                <span
                  className={`flex h-6 w-[68px] shrink-0 items-center justify-center rounded-lg px-1.5 text-center text-[9.5px] font-semibold tabular-nums ${
                    isCurrent ? "bg-accent text-accent-ink" : "bg-panel-2 text-muted"
                  }`}
                >
                  {formatYear(targetYear, lang)}
                </span>
                <span className="min-w-0">
                  <span
                    className={`block truncate text-[11.5px] leading-snug ${
                      isCurrent ? "font-semibold text-ink" : "font-medium text-ink/90"
                    }`}
                  >
                    {title}
                  </span>
                  <span className="mt-0.5 flex items-center justify-between gap-2 text-[10px] text-muted">
                    <span className="truncate">{range}</span>
                    {targetEntry ? (
                      <span className="shrink-0 tabular-nums text-muted/80">
                        {targetEntry.feature_count} {ui.featureCount}
                      </span>
                    ) : null}
                  </span>
                </span>
              </button>
            );
          })}
        </div>

        {/* milestone events */}
        <div className="space-y-1 border-t border-line/60 pt-2.5">
          <div className="flex items-center justify-between px-2 pb-1">
            <span className="text-[9.5px] font-semibold uppercase tracking-[0.12em] text-muted">
              {ui.observed}
            </span>
            <span className="text-[9.5px] font-medium tabular-nums text-muted">
              3000 {ui.timeRangePresent}
            </span>
          </div>
          {timeline.map((item, itemIndex) => {
            if (item.year < -3000) return null;
            const active = itemIndex === index;
            const itemPeriod = getPeriodForYear(item.year);
            const periodLabel = getPeriodName(itemPeriod, lang);
            return (
              <button
                key={item.year}
                type="button"
                onClick={() => setIndex(itemIndex)}
                className={`grid w-full grid-cols-[68px_minmax(0,1fr)] items-start gap-2.5 rounded-xl px-2 py-2 text-left transition ${
                  active
                    ? "bg-tab-active shadow-xs"
                    : "hover:bg-panel-2/80"
                }`}
              >
                <span
                  className={`mt-0.5 flex h-6 w-[68px] shrink-0 items-center justify-center rounded-lg px-1.5 text-center text-[9.5px] font-semibold tabular-nums ${
                    active ? "bg-accent text-accent-ink" : "bg-panel-2 text-muted"
                  }`}
                >
                  {item.month && item.year > 0 && item.precision !== "year"
                    ? `${String(item.month).padStart(2, "0")}/${item.year}`
                    : formatYear(item.year, lang)}
                </span>
                <span className="min-w-0">
                  <span
                    className={`block text-[11.5px] leading-snug ${
                      active ? "font-semibold text-ink" : "font-medium text-ink/90"
                    }`}
                  >
                    {localizedEvent(item, lang)}
                  </span>
                  <span className="mt-0.5 flex items-center justify-between gap-2 text-[10px] text-muted">
                    <span className="truncate">{periodLabel}</span>
                    <span className="shrink-0 tabular-nums text-muted/80">
                      {item.feature_count} {ui.featureCount}
                    </span>
                  </span>
                </span>
              </button>
            );
          })}
        </div>
      </div>
    </aside>
  );
}
