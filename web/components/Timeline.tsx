"use client";

import { useEffect, useRef, useState } from "react";
import type {
  Dispatch,
  KeyboardEvent as ReactKeyboardEvent,
  PointerEvent as ReactPointerEvent,
  SetStateAction
} from "react";
import { Icon } from "./Icons";
import {
  formatYear,
  localizedEra,
  yearParts
} from "@/lib/format";
import {
  ERA_BANDS,
  MAX_YEAR,
  MIN_YEAR,
  TICK_YEARS,
  fractionToYear,
  getPeriodForYear,
  getPeriodName,
  getPeriodRange,
  getPeriodShort,
  parseYearInput,
  yearToFraction
} from "@/lib/timeline";
import { getLocale } from "@/lib/i18n";
import type { Lang, StepMode, TimelineEntry, UILabels } from "@/lib/types";

const MONTH_NAMES_EN = [
  "Jan", "Feb", "Mar", "Apr", "May", "Jun",
  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"
];

function edgeTransform(fraction: number) {
  if (fraction <= 0.03) return "translateX(0)";
  if (fraction >= 0.97) return "translateX(-100%)";
  return "translateX(-50%)";
}

function parseYearMonthInput(input: string): { year: number; month: number | null } | null {
  const trimmed = input.trim();
  if (!trimmed) return null;

  // supports mm/yyyy or yyyy-mm formats
  const slashMatch = trimmed.match(/^(\d{1,2})[\/-](\d{1,4})(?:\s*(bce|bc|tcn|ad|ce|scn))?$/i);
  if (slashMatch) {
    const month = Math.min(12, Math.max(1, parseInt(slashMatch[1], 10)));
    let year = parseInt(slashMatch[2], 10);
    const era = slashMatch[3]?.toLowerCase();
    if (era === "bc" || era === "bce" || era === "tcn") year = -year;
    return { year, month };
  }

  const isoMatch = trimmed.match(/^(-?\d{1,4})[\/-](\d{1,2})$/);
  if (isoMatch) {
    const year = parseInt(isoMatch[1], 10);
    const month = Math.min(12, Math.max(1, parseInt(isoMatch[2], 10)));
    return { year, month };
  }

  const year = parseYearInput(trimmed);
  if (year !== null) return { year, month: null };
  return null;
}

function JumpInput({
  ui,
  value,
  onChange,
  onCommit
}: {
  ui: UILabels;
  value: string;
  onChange: (value: string) => void;
  onCommit: () => void;
}) {
  return (
    <label className="relative block h-9 w-[114px] rounded-xl border border-line bg-transparent px-2.5 pb-1 pt-1 transition focus-within:border-accent/70 focus-within:ring-2 focus-within:ring-accent-soft sm:h-10 sm:w-[124px] sm:pt-1.5">
      <span className="pointer-events-none absolute -top-[6px] left-2 bg-timeline px-1 text-[9.5px] font-medium text-muted">
        {ui.jumpToYear}
      </span>
      <input
        value={value}
        onChange={(event) => onChange(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === "Enter" || event.key === "Escape") {
            event.preventDefault();
            onCommit();
            event.currentTarget.blur();
          }
        }}
        onBlur={onCommit}
        onFocus={(event) => event.currentTarget.select()}
        inputMode="text"
        spellCheck={false}
        aria-label={ui.jumpToYear}
        className="mt-0.5 w-full bg-transparent text-[12.5px] font-semibold tabular-nums text-ink outline-none sm:text-[13px]"
      />
    </label>
  );
}

interface TimelineProps {
  timeline: TimelineEntry[];
  index: number;
  year: number;
  month: number | null;
  stepMode: StepMode;
  setStepMode: (mode: StepMode) => void;
  onYearMonthChange: (year: number, month: number | null) => void;
  onStepPrev: () => void;
  onStepNext: () => void;
  lang: Lang;
  ui: UILabels;
  playing: boolean;
  onTogglePlay: () => void;
  speed: number;
  setSpeed: Dispatch<SetStateAction<number>>;
}

export default function Timeline({
  timeline,
  index,
  year,
  month,
  stepMode,
  setStepMode,
  onYearMonthChange,
  onStepPrev,
  onStepNext,
  lang,
  ui,
  playing,
  onTogglePlay,
  speed,
  setSpeed
}: TimelineProps) {
  const layer = timeline[index] || null;
  const effectiveYear = year + (month ? (month - 1) / 12 : 0);
  const fraction = yearToFraction(effectiveYear);

  const [jumpValue, setJumpValue] = useState("");
  const [mobileCollapsed, setMobileCollapsed] = useState(false);
  const trackRef = useRef<HTMLDivElement>(null);
  const draggingRef = useRef(false);

  useEffect(() => {
    if (month) {
      setJumpValue(`${month}/${year}`);
    } else {
      setJumpValue(formatYear(year, lang));
    }
  }, [lang, month, year]);

  if (!layer) return null;

  const parts = yearParts(year, lang);
  const currentPeriod = getPeriodForYear(year);
  const eraName = getPeriodName(currentPeriod, lang) || localizedEra(layer, lang);
  const eraRange = getPeriodRange(currentPeriod, lang);
  const era = `${eraName} (${eraRange})`;
  const monthLabel = month ? getLocale(lang).formatMonthYear(month, "").trim() : null;

  function updateFromClientX(clientX: number) {
    const track = trackRef.current;
    if (!track) return;
    const rect = track.getBoundingClientRect();
    const nextFraction = Math.min(1, Math.max(0, (clientX - rect.left) / Math.max(1, rect.width)));

    const rawYear = fractionToYear(nextFraction);
    if (stepMode === "100y") {
      const stepped = Math.min(MAX_YEAR, Math.max(MIN_YEAR, Math.round(rawYear / 100) * 100));
      onYearMonthChange(stepped, null);
    } else if (stepMode === "10y") {
      const stepped = Math.min(MAX_YEAR, Math.max(MIN_YEAR, Math.round(rawYear / 10) * 10));
      onYearMonthChange(stepped, null);
    } else if (stepMode === "1y") {
      const stepped = Math.min(MAX_YEAR, Math.max(MIN_YEAR, Math.round(rawYear)));
      onYearMonthChange(stepped, null);
    } else if (stepMode === "month") {
      const floored = Math.floor(rawYear);
      const monthRatio = Math.max(0, Math.min(0.999, rawYear - floored));
      const m = Math.min(12, Math.max(1, Math.floor(monthRatio * 12) + 1));
      const stepped = Math.min(MAX_YEAR, Math.max(MIN_YEAR, floored));
      onYearMonthChange(stepped, m);
    }
  }

  function handleTrackDown(event: ReactPointerEvent<HTMLDivElement>) {
    event.preventDefault();
    draggingRef.current = true;
    event.currentTarget.setPointerCapture?.(event.pointerId);
    updateFromClientX(event.clientX);
  }

  function handleTrackMove(event: ReactPointerEvent<HTMLDivElement>) {
    if (!draggingRef.current) return;
    updateFromClientX(event.clientX);
  }

  function handleTrackUp(event: ReactPointerEvent<HTMLDivElement>) {
    draggingRef.current = false;
    if (event.currentTarget.hasPointerCapture?.(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId);
    }
  }

  function handleTrackKey(event: ReactKeyboardEvent<HTMLDivElement>) {
    if (event.key === "ArrowLeft") {
      event.preventDefault();
      onStepPrev();
    } else if (event.key === "ArrowRight") {
      event.preventDefault();
      onStepNext();
    } else if (event.key === "Home") {
      event.preventDefault();
      onYearMonthChange(MIN_YEAR, null);
    } else if (event.key === "End") {
      event.preventDefault();
      onYearMonthChange(MAX_YEAR, null);
    }
  }

  function commitJump() {
    const parsed = parseYearMonthInput(jumpValue);
    if (!parsed) {
      setJumpValue(month ? `${month}/${year}` : formatYear(year, lang));
      return;
    }
    onYearMonthChange(parsed.year, parsed.month);
  }

  const stepModes: Array<{ id: StepMode; label: string }> = [
    { id: "100y", label: ui.step100y },
    { id: "10y", label: ui.step10y },
    { id: "1y", label: ui.step1y },
    { id: "month", label: ui.stepMonth }
  ];

  return (
    <section className="shrink-0 px-0 pb-0 sm:px-5 sm:pb-4">
      <div
        className={`relative border-t border-line bg-timeline px-3.5 transition-all sm:rounded-[22px] sm:border sm:px-6 sm:py-3.5 sm:shadow-[0_-8px_30px_rgba(0,0,0,0.10)] ${
          mobileCollapsed ? "py-2" : "py-2.5"
        }`}
      >
        {/* top bar: era info, step controls, and playback */}
        <div className="flex flex-nowrap items-center justify-between gap-1.5 sm:gap-3">
          <div className="flex min-w-0 flex-1 items-center gap-1.5 overflow-hidden sm:gap-3.5">
            <div className="flex shrink-0 items-baseline gap-1 whitespace-nowrap sm:gap-1.5">
              {monthLabel ? (
                <span
                  className={`font-semibold tracking-tight text-accent ${
                    mobileCollapsed ? "text-[11.5px] sm:text-[18px]" : "text-[12.5px] sm:text-[18px]"
                  }`}
                >
                  {monthLabel}
                </span>
              ) : null}
              <span
                className={`font-semibold leading-none tracking-[-0.04em] tabular-nums text-ink ${
                  mobileCollapsed
                    ? "text-[19px] sm:text-[34px]"
                    : monthLabel
                      ? "text-[20px] sm:text-[34px]"
                      : "text-[23px] sm:text-[34px]"
                }`}
              >
                {parts.number}
              </span>
              <span className="text-[10px] font-semibold tracking-wide text-accent sm:text-[13px]">
                {parts.suffix}
              </span>
            </div>
            {mobileCollapsed ? (
              <span className="min-w-0 flex-1 truncate text-[11px] font-medium text-muted sm:hidden">
                · {era}
              </span>
            ) : null}
            <div className="hidden min-w-0 flex-1 sm:block">
              <p className="truncate text-[14px] font-semibold leading-snug text-ink">{era}</p>
              <p className="truncate text-[11px] text-muted">
                {playing ? ui.playing : ui.paused} · {speed}× · {ui.dragHint}
              </p>
            </div>
          </div>

          <div className="flex shrink-0 items-center gap-1 sm:gap-2">
            <div
              className={`${
                mobileCollapsed ? "hidden sm:flex" : "flex"
              } h-8 shrink-0 items-center rounded-full bg-control/70 p-0.5 sm:h-10 sm:p-1`}
              role="group"
              aria-label={ui.stepMode}
            >
              {stepModes.map((mode) => {
                const active = stepMode === mode.id;
                return (
                  <button
                    key={mode.id}
                    type="button"
                    onClick={() => {
                      setStepMode(mode.id);
                      if (mode.id === "month" && !month) {
                        onYearMonthChange(year, 1);
                      } else if (mode.id !== "month" && month) {
                        onYearMonthChange(year, null);
                      }
                    }}
                    className={`h-full whitespace-nowrap rounded-full px-1.5 text-[9.5px] font-semibold transition sm:px-3 sm:text-[11.5px] ${
                      active
                        ? "bg-accent text-accent-ink shadow-sm"
                        : "text-muted hover:text-ink"
                    }`}
                  >
                    {mode.label}
                  </button>
                );
              })}
            </div>

            <button
              type="button"
              onClick={onTogglePlay}
              aria-label={playing ? ui.pause : ui.play}
              title={playing ? ui.pause : ui.play}
              className="grid size-8 shrink-0 place-items-center rounded-xl bg-accent text-accent-ink shadow-sm transition hover:brightness-105 active:scale-95 sm:size-10"
            >
              <Icon name={playing ? "pause" : "play"} size={20} />
            </button>

            <div className={`${mobileCollapsed ? "hidden sm:block" : "block"} relative shrink-0`}>
              <select
                value={speed}
                onChange={(event) => setSpeed(Number(event.target.value))}
                aria-label="Playback speed"
                className="h-8 appearance-none whitespace-nowrap rounded-full bg-control pl-2 pr-5 text-[10.5px] font-semibold text-ink outline-none transition hover:brightness-105 sm:h-10 sm:pl-3.5 sm:pr-7 sm:text-[12px]"
              >
                <option value={1}>1×</option>
                <option value={2}>2×</option>
                <option value={4}>4×</option>
              </select>
              <Icon
                name="chevron"
                size={15}
                className="pointer-events-none absolute right-1 top-1/2 -translate-y-1/2 text-muted sm:right-2"
              />
            </div>

            <div className="hidden shrink-0 sm:block">
              <JumpInput
                ui={ui}
                value={jumpValue}
                onChange={setJumpValue}
                onCommit={commitJump}
              />
            </div>

            <button
              type="button"
              onClick={() => setMobileCollapsed((prev) => !prev)}
              aria-label={mobileCollapsed ? ui.showMore : ui.showLess}
              title={mobileCollapsed ? ui.showMore : ui.showLess}
              className="grid size-8 shrink-0 place-items-center rounded-xl bg-control text-control-ink transition active:scale-95 sm:hidden"
            >
              <Icon
                name="chevron"
                size={18}
                className={`transition duration-200 ${mobileCollapsed ? "rotate-180" : ""}`}
              />
            </button>
          </div>
        </div>

        {/* non-linear timeline track */}
        <div className={mobileCollapsed ? "mt-1.5 sm:mt-2" : "mt-2 sm:mt-2.5"}>
          <div
            className="relative -mx-1 cursor-pointer touch-none px-1 py-1.5 outline-none focus-visible:ring-2 focus-visible:ring-accent/60"
            role="slider"
            tabIndex={0}
            aria-label={ui.jumpToYear}
            aria-valuemin={MIN_YEAR}
            aria-valuemax={MAX_YEAR}
            aria-valuenow={year}
            aria-valuetext={monthLabel ? `${monthLabel} ${formatYear(year, lang)}` : formatYear(year, lang)}
            onPointerDown={handleTrackDown}
            onPointerMove={handleTrackMove}
            onPointerUp={handleTrackUp}
            onPointerCancel={handleTrackUp}
            onKeyDown={handleTrackKey}
          >
            <div ref={trackRef} className="relative h-1.5 w-full rounded-full bg-control">
              <div
                className="absolute inset-y-0 left-0 rounded-full bg-accent"
                style={{ width: `${fraction * 100}%` }}
              />
              <div className="pointer-events-none absolute inset-x-0 top-[7px] h-1">
                {timeline.map((item) => (
                  <span
                    key={item.year}
                    className="absolute top-0 h-1 w-px bg-line-strong/35"
                    style={{ left: `${yearToFraction(item.year) * 100}%` }}
                  />
                ))}
              </div>
              {/* current scrubber thumb */}
              <span
                className="pointer-events-none absolute top-1/2 h-4 w-[3px] -translate-x-1/2 -translate-y-1/2 rounded-full bg-accent shadow-[0_0_6px_var(--accent)] sm:h-5"
                style={{ left: `${fraction * 100}%` }}
              />
            </div>
          </div>

          <div className={`${mobileCollapsed ? "hidden sm:block" : "block"} relative mt-1 h-3.5 sm:mt-1.5`}>
            {TICK_YEARS.map((tickYear) => {
              const tickFraction = yearToFraction(tickYear);
              return (
                <span
                  key={tickYear}
                  className="absolute top-0 whitespace-nowrap text-[10px] font-medium tabular-nums text-muted"
                  style={{
                    left: `${tickFraction * 100}%`,
                    transform: edgeTransform(tickFraction)
                  }}
                >
                  {formatYear(tickYear, lang)}
                </span>
              );
            })}
          </div>

          <div className="relative mt-1 hidden h-4 sm:block">
            {ERA_BANDS.map((band) => {
              const start = yearToFraction(band.from);
              const end = yearToFraction(band.to);
              const width = Math.max(0.02, end - start);
              const isActive = currentPeriod.id === band.id;
              const fullTitle = `${getPeriodName(band, lang)} (${getPeriodRange(band, lang)})`;
              return (
                <button
                  key={band.id}
                  type="button"
                  onClick={() => onYearMonthChange(band.jumpYear, null)}
                  title={fullTitle}
                  className={`absolute top-0 truncate border-r border-line/40 px-1 text-center text-[8.5px] font-semibold uppercase tracking-[0.06em] transition last:border-r-0 hover:text-ink ${
                    isActive ? "text-accent" : "text-muted"
                  }`}
                  style={{
                    left: `${start * 100}%`,
                    width: `${width * 100}%`
                  }}
                >
                  {getPeriodShort(band, lang)}
                </button>
              );
            })}
          </div>
        </div>

        {!mobileCollapsed ? (
          <div className="mt-1 flex items-center justify-between gap-2 sm:hidden">
            <div className="min-w-0">
              <p className="truncate text-[12.5px] font-semibold text-ink">{era}</p>
              <p className="truncate text-[10px] text-muted">
                {playing ? ui.playing : ui.paused} · {speed}×
              </p>
            </div>
            <JumpInput ui={ui} value={jumpValue} onChange={setJumpValue} onCommit={commitJump} />
          </div>
        ) : null}
      </div>
    </section>
  );
}
