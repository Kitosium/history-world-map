"use client";

import { useMemo } from "react";
import type { CSSProperties } from "react";
import { formatYear } from "@/lib/format";
import type {
  EntityIndex,
  FeatureCollection,
  Lang,
  MapSize,
  UILabels,
  View
} from "@/lib/types";

interface LegendProps {
  layer: FeatureCollection | null;
  entitiesById?: Record<string, EntityIndex>;
  lang: Lang;
  ui: UILabels;
  year?: number | null;
  view?: View | null;
  size?: MapSize;
  className?: string;
  style?: CSSProperties;
}

export default function Legend({
  layer,
  lang,
  ui,
  year,
  className = "",
  style
}: LegendProps) {
  const hasApproximate = useMemo(() => {
    return Boolean(
      layer?.features?.some(
        (feature) => (feature.properties?.border_precision ?? 2) <= 1
      )
    );
  }, [layer]);

  if (!layer?.features?.length) return null;

  return (
    <div style={style} className={`pointer-events-none ${className}`}>
      <div className="w-[184px] rounded-2xl bg-legend p-3 panel-shadow sm:w-[196px]">
        <p className="flex items-baseline gap-1.5 text-[9.5px] font-semibold uppercase tracking-[0.14em] text-ink sm:text-[10px]">
          <span>{ui.legend}</span>
          <span className="text-faint">·</span>
          <span className="text-ink/80">{formatYear(year, lang)}</span>
        </p>

        {/* boundary precision legend */}
        <div className="mt-2 space-y-1.5 pt-0.5">
          <div className="flex items-center gap-2">
            <span className="h-0 w-3.5 shrink-0 border-t-2 border-line-strong" />
            <span className="text-[10px] text-muted">
              {ui.boundaryGeoreferenced}
            </span>
          </div>
          {hasApproximate ? (
            <div className="flex items-center gap-2">
              <span className="h-0 w-3.5 shrink-0 border-t-2 border-dashed border-muted/70" />
              <span className="text-[10px] text-muted">
                {ui.approximateShort}
              </span>
            </div>
          ) : null}
        </div>
      </div>

      <p className="mt-1.5 px-1 text-[9.5px] font-medium text-muted sm:hidden">
        {ui.attribution} · {ui.schematicExtent}
      </p>
    </div>
  );
}
