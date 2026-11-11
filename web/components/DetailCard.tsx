"use client";

import { useEffect, useState } from "react";
import { Icon } from "./Icons";
import {
  confidenceLabel,
  formatDetailedSpan,
  formatSpan,
  formatYear,
  formatYearMonth,
  localizedDescription,
  localizedName,
  secondaryName,
  sourceTitle
} from "@/lib/format";
import { getLocale, typeLabel } from "@/lib/i18n";
import type {
  EntityDocument,
  EntityLike,
  Lang,
  SourceRecord,
  UILabels,
  Variant
} from "@/lib/types";

function MetaItem({ label, value }: { label: string; value?: string | null }) {
  return (
    <div className="min-w-0">
      <p className="text-[10.5px] font-medium text-muted">{label}</p>
      <p className="mt-0.5 truncate text-[12.5px] font-semibold text-ink">{value || "—"}</p>
    </div>
  );
}

function SourceList({
  sourceIds,
  sourcesById,
  confidenceBasis,
  ui,
  lang
}: {
  sourceIds: string[];
  sourcesById: Record<string, SourceRecord>;
  confidenceBasis: string;
  ui: UILabels;
  lang: Lang;
}) {
  return (
    <div className="fade-in mt-3 space-y-1.5 rounded-[14px] bg-panel-2 p-2.5">
      {sourceIds.length === 0 ? (
        <p className="px-1.5 py-1 text-[11px] text-muted">—</p>
      ) : (
        sourceIds.map((sourceId) => {
          const source = sourcesById?.[sourceId];
          const title = sourceTitle(source, lang);
          const url = source?.urls?.[0];
          return (
            <div
              key={sourceId}
              className="flex items-start gap-2 rounded-lg px-1.5 py-1.5 text-[11px] leading-snug text-muted"
            >
              <span className="mt-1 size-1.5 shrink-0 rounded-full bg-accent/70" />
              {url ? (
                <a
                  href={url}
                  target="_blank"
                  rel="noreferrer"
                  className="min-w-0 flex-1 transition hover:text-ink hover:underline"
                >
                  {title}
                </a>
              ) : (
                <span className="min-w-0 flex-1">{title}</span>
              )}
            </div>
          );
        })
      )}
      {confidenceBasis ? (
        <div className="mt-1 border-t border-line px-1.5 pt-2">
          <p className="text-[9.5px] font-semibold uppercase tracking-[0.14em] text-muted">
            {ui.confidenceBasis}
          </p>
          <p className="mt-1 text-[11px] leading-snug text-muted">{confidenceBasis}</p>
        </div>
      ) : null}
    </div>
  );
}

interface DetailCardProps {
  detail: EntityDocument | null;
  indexItem: EntityLike | null;
  sourcesById: Record<string, SourceRecord>;
  lang: Lang;
  ui: UILabels;
  onClose: () => void;
  year?: number | null;
  month?: number | null;
  variant?: Variant;
}

export default function DetailCard({
  detail,
  indexItem,
  sourcesById,
  lang,
  ui,
  onClose,
  year,
  month,
  variant = "card"
}: DetailCardProps) {
  const [sourcesOpen, setSourcesOpen] = useState(false);
  const [expanded, setExpanded] = useState(false);
  const entity = detail || indexItem;

  useEffect(() => {
    setSourcesOpen(false);
    setExpanded(false);
  }, [entity?.id]);

  if (!entity) return null;

  const name = localizedName(entity, lang);
  const secondary = secondaryName(entity, lang);
  const type = detail?.type || indexItem?.type || "state";
  const fromYear = detail?.existence?.from?.year ?? indexItem?.from_year ?? null;
  const fromMonth = detail?.existence?.from?.month ?? (indexItem as any)?.from_month ?? null;
  const fromDay = detail?.existence?.from?.day ?? (indexItem as any)?.from_day ?? null;
  const toYear = detail?.existence?.to?.year ?? indexItem?.to_year ?? null;
  const toMonth = detail?.existence?.to?.month ?? (indexItem as any)?.to_month ?? null;
  const toDay = detail?.existence?.to?.day ?? (indexItem as any)?.to_day ?? null;
  const observed = detail?.observed_periods?.length ?? indexItem?.observed_year_count ?? null;
  const confidence = detail?.confidence || indexItem?.confidence || "low";
  const confidenceBasis = detail?.confidence_basis || indexItem?.confidence_basis || "";
  const boundaryPrecision =
    detail?.spatial_coverage?.boundary_precision || indexItem?.boundary_precision || "";
  const approximate =
    boundaryPrecision.includes("approximate") || boundaryPrecision === "mixed";
  const description = localizedDescription(detail || indexItem, lang);
  const status = Number(toYear) >= 2026 ? ui.contemporary : ui.historical;
  const sourceIds = detail?.source_ids || indexItem?.source_ids || [];
  const wikidataId = detail?.wikidata_id || indexItem?.wikidata_id;
  const wikipedia =
    detail?.external_links?.wikipedia ||
    `https://${getLocale(lang).wikiPrefix}.wikipedia.org/wiki/Special:Search?search=${encodeURIComponent(
      name
    )}`;
  const sourceTitles = sourceIds
    .map((sourceId) => sourceTitle(sourcesById?.[sourceId], lang))
    .filter((title) => title && title !== "—");

  const isSheet = variant === "sheet";
  const dateSpan = formatDetailedSpan(
    fromYear,
    fromMonth,
    fromDay,
    toYear,
    toMonth,
    toDay,
    lang,
    detail?.existence?.status || (indexItem as any)?.status
  );
  const yearLabel =
    year !== null && year !== undefined
      ? month
        ? formatYearMonth(year, month, lang)
        : formatYear(year, lang)
      : dateSpan;

  return (
    <aside
      className={`pointer-events-auto bg-panel panel-shadow ${
        isSheet
          ? "thin-scrollbar max-h-[42vh] overflow-y-auto rounded-t-2xl border-t border-line px-3.5 pb-3 pt-2"
          : "thin-scrollbar max-h-[calc(100dvh-310px)] w-[330px] overflow-y-auto rounded-2xl p-4 sm:p-5"
      }`}
    >
      {isSheet ? (
        <div className="mx-auto mb-1.5 h-1 w-8 rounded-full bg-line-strong/70" />
      ) : null}

      <div className="flex items-start justify-between gap-2.5">
        <div className="min-w-0 flex-1">
          <p className="flex flex-wrap items-center gap-x-1.5 gap-y-0.5 text-[10px] font-semibold uppercase tracking-[0.08em]">
            <span className="text-accent">{typeLabel(type, lang)}</span>
            <span className="text-faint">·</span>
            <span className="normal-case tracking-normal text-muted">
              {isSheet ? yearLabel : dateSpan}
            </span>
            {!isSheet ? (
              <>
                <span className="text-faint">·</span>
                <span className="normal-case tracking-normal text-muted">{status}</span>
              </>
            ) : null}
          </p>
          <h2
            className={`mt-0.5 font-semibold leading-tight tracking-[-0.02em] text-ink ${
              isSheet ? "truncate text-[17px]" : "text-[20px]"
            }`}
          >
            {name}
          </h2>
          {secondary ? (
            <p className="mt-0.5 truncate text-[11px] text-muted">{secondary}</p>
          ) : null}
        </div>

        <button
          type="button"
          onClick={onClose}
          aria-label={ui.close}
          className="grid size-7 shrink-0 place-items-center rounded-full bg-panel-2/80 text-muted transition hover:bg-control hover:text-ink"
        >
          <Icon name="close" size={17} />
        </button>
      </div>

      <p
        className={`mt-2 text-[12.5px] leading-[1.5] text-ink/90 sm:text-[13px] ${
          isSheet && !expanded ? "line-clamp-2" : ""
        } ${description ? "" : "italic text-muted"}`}
      >
        {description || ui.noDescription}
      </p>

      {isSheet ? (
        <div className="mt-2.5 flex items-center justify-between gap-2 rounded-xl bg-panel-2/75 px-2.5 py-1.5">
          <div className="flex min-w-0 flex-1 items-center gap-1.5 text-[11px] text-muted">
            <Icon name="info" size={15} className="shrink-0 text-accent" />
            <span className="truncate">
              {approximate ? ui.boundaryApproximateShort : ui.boundaryGeoreferenced}
            </span>
            <span className="text-faint">·</span>
            <button
              type="button"
              onClick={() => setSourcesOpen((value) => !value)}
              className="shrink-0 font-semibold text-ink underline-offset-2 transition hover:underline"
            >
              {ui.sourcesShort}
            </button>
          </div>
          <button
            type="button"
            onClick={() => setExpanded((value) => !value)}
            className="flex shrink-0 items-center gap-1 rounded-lg bg-control px-2 py-1 text-[11px] font-semibold text-control-ink transition active:scale-95"
          >
            {expanded ? ui.showLess : ui.showMore}
            <Icon
              name="chevron"
              size={15}
              className={`transition ${expanded ? "rotate-180" : ""}`}
            />
          </button>
        </div>
      ) : null}

      {sourcesOpen ? (
        <SourceList
          sourceIds={sourceIds}
          sourcesById={sourcesById}
          confidenceBasis={confidenceBasis}
          ui={ui}
          lang={lang}
        />
      ) : null}

      {!isSheet || expanded ? (
        <>
          <div className="mt-3 grid grid-cols-2 gap-x-3 gap-y-2 rounded-xl bg-panel-2/50 p-2.5 sm:mt-3.5 sm:bg-transparent sm:p-0">
            <MetaItem label={ui.period} value={formatSpan(fromYear, toYear, lang)} />
            <MetaItem label={ui.confidence} value={confidenceLabel(confidence, lang)} />
            <MetaItem
              label={ui.observed}
              value={observed ? `${observed} ${ui.allSnapshots}` : "—"}
            />
            <MetaItem label={ui.type} value={typeLabel(type, lang)} />
          </div>

          <div className="mt-3 rounded-xl bg-info px-3 py-2.5 sm:mt-3.5 sm:px-3.5">
            <p className="flex items-center gap-1.5 text-[12px] font-semibold text-ink sm:text-[12.5px]">
              <Icon name="info" size={16} className="text-accent" />
              {approximate ? ui.boundaryApproximate : ui.boundaryGeoreferenced}
            </p>
            <p className="mt-1 text-[11px] leading-[1.48] text-muted sm:text-[11.5px]">
              {approximate ? ui.approximateNote : ui.boundaryModernNote}
            </p>
          </div>

          {!isSheet ? (
            <button
              type="button"
              onClick={() => setSourcesOpen((value) => !value)}
              className="mt-3 inline-flex items-center gap-1.5 rounded-xl border border-line px-3 py-2 text-left text-[12px] font-semibold text-ink transition hover:bg-panel-2"
            >
              <Icon name="book" size={16} className="text-accent" />
              {ui.sources}
              <Icon name="external" size={14} className="text-muted" />
            </button>
          ) : null}

          <div className="mt-3 flex items-center gap-3 text-[11px] font-medium text-muted">
            <a
              href={wikipedia}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1 transition hover:text-ink hover:underline"
            >
              <Icon name="external" size={14} />
              {ui.wikipedia}
            </a>
            {wikidataId ? (
              <a
                href={`https://www.wikidata.org/wiki/${wikidataId}`}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1 transition hover:text-ink hover:underline"
              >
                <Icon name="tag" size={14} />
                {ui.wikidata}
              </a>
            ) : null}
          </div>
          {confidenceBasis || sourceTitles.length ? (
            <p className="mt-1.5 text-[11px] leading-[1.45] text-muted">
              {confidenceBasis}
              {sourceTitles.length ? ` · ${sourceTitles.join("; ")}` : ""}
            </p>
          ) : null}
        </>
      ) : null}
    </aside>
  );
}
