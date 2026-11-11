"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type {
  Dispatch,
  MouseEvent as ReactMouseEvent,
  PointerEvent as ReactPointerEvent,
  SetStateAction
} from "react";
import {
  geometryToPath,
  graticulePath,
  isBboxVisible,
  panView,
  processFeatureGeometry,
  project,
  scaleBarMetrics,
  viewToTransform,
  worldToScreen,
  zoomViewAt
} from "@/lib/geo";
import { formatSpan, localizedName, truncate } from "@/lib/format";
import { typeLabel } from "@/lib/i18n";
import { assignFourColors, featureColor } from "@/lib/colors";
import type {
  EntityIndex,
  FeatureCollection,
  FeatureMetrics,
  GeoFeature,
  GeoFeatureProperties,
  Lang,
  LayerToggles,
  MapSize,
  Transform,
  UserLocation,
  View
} from "@/lib/types";

type Rect = [number, number, number, number];

interface MapFeature {
  feature: GeoFeature;
  properties: GeoFeatureProperties;
  entity: EntityIndex | null;
  id: string;
  name: string;
  type: string;
  color: string;
  metrics: FeatureMetrics;
  path: string;
}

interface MapLabel {
  id: string;
  text: string;
  x: number;
  y: number;
  fontSize: number;
  letterSpacing: number;
  isSelected: boolean;
}

interface DragState {
  active: boolean;
  moved: boolean;
  pointerId: number | null;
  startX: number;
  startY: number;
  lastDx: number;
  lastDy: number;
  startView: View | null;
}

interface PinchState {
  distance: number;
  midX: number;
  midY: number;
  view: View;
}

interface PointEvent {
  clientX: number;
  clientY: number;
}

interface MapCanvasProps {
  layer: FeatureCollection | null;
  land: FeatureCollection | null;
  entitiesById: Record<string, EntityIndex>;
  lang: Lang;
  selectedId: string | null;
  onSelect: (id: string, properties: GeoFeatureProperties | null) => void;
  onClear: () => void;
  view: View | null;
  setView: Dispatch<SetStateAction<View | null>>;
  onSizeChange: (size: MapSize) => void;
  layers: LayerToggles;
  userLocation?: UserLocation | null;
  userLocationLabel?: string;
}

function overlaps(a: Rect, b: Rect, padding = 0) {
  return (
    a[0] < b[0] + b[2] + padding &&
    a[0] + a[2] + padding > b[0] &&
    a[1] < b[1] + b[3] + padding &&
    a[1] + a[3] + padding > b[1]
  );
}

export default function MapCanvas({
  layer,
  land,
  entitiesById,
  lang,
  selectedId,
  onSelect,
  onClear,
  view,
  setView,
  onSizeChange,
  layers,
  userLocation = null,
  userLocationLabel
}: MapCanvasProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const panGroupRef = useRef<SVGGElement>(null);
  const labelsGroupRef = useRef<SVGGElement>(null);
  const [size, setSize] = useState<MapSize>({ width: 0, height: 0 });
  const [hoveredId, setHoveredId] = useState<string | null>(null);
  const [cursor, setCursor] = useState("grab");
  const tooltipRef = useRef<HTMLDivElement>(null);

  const dragRef = useRef<DragState>({
    active: false,
    moved: false,
    pointerId: null,
    startX: 0,
    startY: 0,
    lastDx: 0,
    lastDy: 0,
    startView: null
  });
  const pointersRef = useRef<Map<number, { x: number; y: number }>>(new Map());
  const pinchRef = useRef<PinchState | null>(null);
  const suppressClickRef = useRef(false);

  useEffect(() => {
    const element = containerRef.current;
    if (!element) return undefined;
    const update = () => {
      const rect = element.getBoundingClientRect();
      const next = { width: Math.round(rect.width), height: Math.round(rect.height) };
      setSize((current) =>
        current.width === next.width && current.height === next.height ? current : next
      );
    };
    update();
    const observer = new ResizeObserver(update);
    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    onSizeChange(size);
  }, [onSizeChange, size]);

  const transform = useMemo(() => {
    if (!view || !size.width || !size.height) return null;
    return viewToTransform(view, size.width, size.height);
  }, [view, size]);

  const landPath = useMemo(() => {
    if (!land?.features) return "";
    return land.features.map((feature) => geometryToPath(feature.geometry)).join("");
  }, [land]);

  const rawFeatures = useMemo(() => {
    if (!layer?.features) return [];
    const colorMap = assignFourColors(layer.features);
    return layer.features.map((feature, index) => {
      const properties: GeoFeatureProperties = feature.properties || {};
      const { path, metrics } = processFeatureGeometry(feature.geometry);
      const id = String(properties.entity_id || feature.id || `feature-${index}`);
      return {
        feature,
        properties,
        id,
        color: colorMap.get(id) || featureColor(properties),
        metrics,
        path
      };
    });
  }, [layer]);

  const features = useMemo<MapFeature[]>(() => {
    return rawFeatures.map((item) => {
      const entity = item.properties.entity_id
        ? entitiesById?.[item.properties.entity_id] || null
        : null;
      return {
        ...item,
        entity,
        name: localizedName(entity || item.properties, lang),
        type: item.properties.type || entity?.type || "state"
      };
    });
  }, [entitiesById, lang, rawFeatures]);

  const drawFeatures = useMemo(
    () => [...features].sort((a, b) => b.metrics.area - a.metrics.area),
    [features]
  );

  // frustum culling: only render svg paths that intersect the current viewport
  const visibleDrawFeatures = useMemo(() => {
    if (!transform || !size.width || !size.height) return drawFeatures;
    return drawFeatures.filter(
      (item) =>
        item.id === selectedId ||
        isBboxVisible(item.metrics.bbox, transform, size.width, size.height, 120)
    );
  }, [drawFeatures, selectedId, size.height, size.width, transform]);

  const selectedFeature = useMemo(
    () => features.find((item) => item.id === selectedId) || null,
    [features, selectedId]
  );
  const hoveredFeature = useMemo(
    () => features.find((item) => item.id === hoveredId) || null,
    [features, hoveredId]
  );

  const labels = useMemo(() => {
    if (!transform || !layers.labels || !size.width) return [];
    const placed: Rect[] = [];
    const result: MapLabel[] = [];
    const compact = size.width < 640;
    const maxLabels = compact ? 9 : 20;
    const headerBottom = compact ? 190 : 136;

    function place(item: MapFeature, isSelected: boolean) {
      if (!item?.name || !item.metrics.area) return;
      const [sx, sy] = worldToScreen(item.metrics.cx, item.metrics.cy, transform as Transform);
      if (sx < 28 || sx > size.width - 28 || sy < 26 || sy > size.height - 26) return;
      if (!isSelected && sy < headerBottom && (sx < 440 || sx > size.width - 92)) return;
      const screenArea = item.metrics.area * (transform as Transform).scale * (transform as Transform).scale;
      if (!isSelected && screenArea < (compact ? 900 : 1200)) return;
      if (!isSelected && result.length >= maxLabels) return;

      // fixed font size and letter spacing for all country labels on canvas
      const fontSize = compact ? 10 : 11;
      const letterSpacing = 1.2;
      const text = truncate(item.name.toUpperCase(), 28);
      const width = text.length * fontSize * 0.6 + letterSpacing * Math.max(0, text.length - 1);
      const height = fontSize * 1.45;
      const rect: Rect = [sx - width / 2, sy - height / 2, width, height];
      if (!isSelected && placed.some((other) => overlaps(rect, other, 7))) return;
      placed.push(rect);
      result.push({
        id: item.id,
        text,
        x: sx,
        y: sy,
        fontSize,
        letterSpacing,
        isSelected
      });
    }

    if (selectedFeature) place(selectedFeature, true);
    for (const item of visibleDrawFeatures) {
      if (selectedFeature && item.id === selectedFeature.id) continue;
      place(item, false);
    }

    // render sovereignty labels for hoàng sa & trường sa at sufficient zoom levels
    const vnPolity = visibleDrawFeatures.find(
      (f) =>
        (f.id === "vietnam" || f.id === "dai-nam" || f.id === "đại-việt" || f.id === "french-indochina") &&
        (f.properties.valid_year ?? 2026) >= 1600
    );
    if (vnPolity && view && view.zoom >= 2.2) {
      const archipelagos = [
        {
          id: "label-hoang-sa",
          lon: 112.0,
          lat: 16.35,
          names: {
            vi: "QĐ. HOÀNG SA (VIỆT NAM)",
            en: "HOÀNG SA / PARACEL IS. (VN)",
            zh: "西沙群岛 (越南黄沙)",
            fr: "ÎLES PARACELS (VIETNAM)"
          } as Record<string, string>
        },
        {
          id: "label-truong-sa",
          lon: 114.2,
          lat: 10.0,
          names: {
            vi: "QĐ. TRƯỜNG SA (VIỆT NAM)",
            en: "TRƯỜNG SA / SPRATLY IS. (VN)",
            zh: "南沙群岛 (越南长沙)",
            fr: "ÎLES SPRATLEYS (VIETNAM)"
          } as Record<string, string>
        }
      ];
      const fontSize = compact ? 10 : 11;
      const letterSpacing = 1.0;
      for (const arch of archipelagos) {
        const [wx, wy] = project(arch.lon, arch.lat);
        const [sx, sy] = worldToScreen(wx, wy, transform as Transform);
        if (sx < 24 || sx > size.width - 24 || sy < 24 || sy > size.height - 24) continue;
        result.push({
          id: arch.id,
          text: arch.names[lang] || arch.names.en || Object.values(arch.names)[0],
          x: sx,
          y: sy,
          fontSize,
          letterSpacing,
          isSelected: selectedId === vnPolity.id
        });
      }
    }

    return result;
  }, [lang, layers.labels, selectedFeature, selectedId, size, transform, view, visibleDrawFeatures]);

  const graticule = useMemo(() => graticulePath(), []);
  const scaleBar = useMemo(
    () => (view && size.width ? scaleBarMetrics(view, size.width) : null),
    [size.width, view]
  );

  const userScreenPos = useMemo(() => {
    if (!userLocation || !transform) return null;
    const [wx, wy] = project(userLocation.lon, userLocation.lat);
    return worldToScreen(wx, wy, transform);
  }, [transform, userLocation]);

  const positionTooltip = useCallback((event: PointEvent) => {
    const container = containerRef.current;
    const tooltip = tooltipRef.current;
    if (!container || !tooltip) return;
    const rect = container.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;
    const left = Math.min(Math.max(12, x + 16), rect.width - 220);
    const top = Math.min(Math.max(12, y + 16), rect.height - 76);
    tooltip.style.setProperty("--tip-x", `${left}px`);
    tooltip.style.setProperty("--tip-y", `${top}px`);
  }, []);

  useEffect(() => {
    const element = containerRef.current;
    if (!element) return undefined;
    function handleWheel(event: WheelEvent) {
      event.preventDefault();
      if (!element || !size.width || !size.height) return;
      const rect = element.getBoundingClientRect();
      const x = event.clientX - rect.left;
      const y = event.clientY - rect.top;
      const factor = Math.exp(-event.deltaY * 0.0016);
      setView((current) =>
        current ? zoomViewAt(current, factor, x, y, size.width, size.height) : current
      );
    }
    element.addEventListener("wheel", handleWheel, { passive: false });
    return () => element.removeEventListener("wheel", handleWheel);
  }, [setView, size.height, size.width]);

  function applyGpuOffset(dx: number, dy: number) {
    const css = dx === 0 && dy === 0 ? "" : `translate3d(${dx}px, ${dy}px, 0)`;
    if (panGroupRef.current) panGroupRef.current.style.transform = css;
    if (labelsGroupRef.current) labelsGroupRef.current.style.transform = css;
  }

  function handlePointerDown(event: ReactPointerEvent<SVGSVGElement>) {
    if (event.pointerType === "mouse" && event.button !== 0) return;
    if (!view) return;
    pointersRef.current.set(event.pointerId, { x: event.clientX, y: event.clientY });
    if (pointersRef.current.size === 2) {
      if (dragRef.current.moved && dragRef.current.startView && size.width) {
        const committed = panView(
          dragRef.current.startView,
          dragRef.current.lastDx,
          dragRef.current.lastDy,
          size.width
        );
        applyGpuOffset(0, 0);
        setView(committed);
      }
      const [first, second] = [...pointersRef.current.values()];
      pinchRef.current = {
        distance: Math.hypot(second.x - first.x, second.y - first.y),
        midX: (first.x + second.x) / 2,
        midY: (first.y + second.y) / 2,
        view
      };
      for (const pointerId of pointersRef.current.keys()) {
        event.currentTarget.setPointerCapture?.(pointerId);
      }
      dragRef.current.active = false;
      suppressClickRef.current = true;
      return;
    }
    if (pointersRef.current.size > 1) return;
    dragRef.current = {
      active: true,
      moved: false,
      pointerId: event.pointerId,
      startX: event.clientX,
      startY: event.clientY,
      lastDx: 0,
      lastDy: 0,
      startView: view
    };
    setCursor("grabbing");
    setHoveredId(null);
  }

  function handlePointerMove(event: ReactPointerEvent<SVGSVGElement>) {
    const tracked = pointersRef.current.get(event.pointerId);
    if (tracked) {
      tracked.x = event.clientX;
      tracked.y = event.clientY;
    }

    if (pointersRef.current.size >= 2 && pinchRef.current && size.width) {
      const [first, second] = [...pointersRef.current.values()];
      const distance = Math.max(1, Math.hypot(second.x - first.x, second.y - first.y));
      const midX = (first.x + second.x) / 2;
      const midY = (first.y + second.y) / 2;
      const start = pinchRef.current;
      const factor = distance / Math.max(1, start.distance);
      setView((current) => {
        if (!current) return current;
        const zoomed = zoomViewAt(start.view, factor, start.midX, start.midY, size.width, size.height);
        return panView(zoomed, midX - start.midX, midY - start.midY, size.width);
      });
      suppressClickRef.current = true;
      return;
    }

    const drag = dragRef.current;
    if (!drag.active || drag.pointerId !== event.pointerId) return;
    const dx = event.clientX - drag.startX;
    const dy = event.clientY - drag.startY;
    if (!drag.moved && Math.hypot(dx, dy) > 4) {
      drag.moved = true;
      event.currentTarget.setPointerCapture?.(event.pointerId);
      setHoveredId(null);
    }
    if (drag.moved && drag.startView) {
      drag.lastDx = dx;
      drag.lastDy = dy;
      applyGpuOffset(dx, dy);
    }
  }

  function finishPointer(event: ReactPointerEvent<SVGSVGElement>) {
    if (event.currentTarget.hasPointerCapture?.(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId);
    }
    pointersRef.current.delete(event.pointerId);
    if (pointersRef.current.size < 2) pinchRef.current = null;
    const drag = dragRef.current;
    if (drag.pointerId === event.pointerId) {
      const moved = drag.moved;
      const startView = drag.startView;
      const dx = drag.lastDx;
      const dy = drag.lastDy;
      drag.active = false;
      drag.moved = false;
      drag.pointerId = null;
      drag.lastDx = 0;
      drag.lastDy = 0;
      setCursor("grab");
      if (moved) {
        suppressClickRef.current = true;
        applyGpuOffset(0, 0);
        if (startView && size.width) {
          setView(panView(startView, dx, dy, size.width));
        }
      }
    }
    if (pointersRef.current.size === 0) {
      window.setTimeout(() => {
        suppressClickRef.current = false;
      }, 0);
    }
  }

  function handleDoubleClick(event: ReactMouseEvent<SVGSVGElement>) {
    if (!view || !size.width || suppressClickRef.current) return;
    const rect = containerRef.current?.getBoundingClientRect();
    if (!rect) return;
    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;
    setView((current) =>
      current ? zoomViewAt(current, 1.7, x, y, size.width, size.height) : current
    );
  }

  function handleBackgroundClick(event: ReactMouseEvent<SVGElement>) {
    if (suppressClickRef.current) return;
    const target = event.target as SVGElement;
    if (event.target === event.currentTarget || target.dataset?.bg === "true") {
      onClear?.();
    }
  }

  function selectFeature(event: ReactMouseEvent<SVGPathElement>, item: MapFeature) {
    event.stopPropagation();
    if (suppressClickRef.current) return;
    onSelect?.(item.id, item.properties);
  }

  return (
    <div
      ref={containerRef}
      className="absolute inset-0 touch-none select-none overflow-hidden bg-map"
    >
      {view && size.width ? (
        <>
      <svg
        width={size.width}
        height={size.height}
        viewBox={`0 0 ${size.width} ${size.height}`}
        className="block h-full w-full"
        style={{ cursor }}
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={finishPointer}
        onPointerCancel={finishPointer}
        onClick={handleBackgroundClick}
        onDoubleClick={handleDoubleClick}
        role="application"
        aria-label="Interactive historical map"
      >
        <defs>
          <pattern
            id="pattern-disputed"
            width="8"
            height="8"
            patternUnits="userSpaceOnUse"
            patternTransform="rotate(45)"
          >
            <rect width="8" height="8" fill="var(--territory-disputed)" fillOpacity="0.38" />
            <line x1="0" y1="0" x2="0" y2="8" stroke="var(--territory-disputed)" strokeWidth="2.5" />
          </pattern>
          <pattern
            id="pattern-disputed-hover"
            width="8"
            height="8"
            patternUnits="userSpaceOnUse"
            patternTransform="rotate(45)"
          >
            <rect width="8" height="8" fill="var(--territory-disputed)" fillOpacity="0.55" />
            <line x1="0" y1="0" x2="0" y2="8" stroke="var(--territory-disputed)" strokeWidth="3" />
          </pattern>
          <pattern
            id="pattern-disputed-selected"
            width="8"
            height="8"
            patternUnits="userSpaceOnUse"
            patternTransform="rotate(45)"
          >
            <rect width="8" height="8" fill="var(--territory-disputed)" fillOpacity="0.65" />
            <line x1="0" y1="0" x2="0" y2="8" stroke="var(--accent)" strokeWidth="3" />
          </pattern>
        </defs>

        <rect data-bg="true" x="0" y="0" width={size.width} height={size.height} fill="var(--map)" />

        {transform ? (
          <g ref={panGroupRef} style={{ willChange: "transform" }}>
            <g transform={`translate(${transform.tx} ${transform.ty}) scale(${transform.scale})`}>
              {landPath ? (
                <path
                  d={landPath}
                  fill="var(--land)"
                  fillRule="evenodd"
                  stroke="var(--land-line)"
                  strokeWidth="0.7"
                  vectorEffect="non-scaling-stroke"
                  onClick={handleBackgroundClick}
                />
              ) : null}

              {layers.graticule ? (
                <path
                  d={graticule}
                  fill="none"
                  stroke="var(--grid)"
                  strokeWidth="0.8"
                  vectorEffect="non-scaling-stroke"
                  pointerEvents="none"
                />
              ) : null}

              {visibleDrawFeatures.map((item) => {
                const isSelected = item.id === selectedId;
                const isHovered = item.id === hoveredId;
                const isDisputed =
                  item.properties.layer_type === "disputed_territory" ||
                  item.properties.type === "disputed_territory";
                const isDependent =
                  item.properties.layer_type === "dependent_territory" ||
                  item.properties.type === "dependent_territory";

                const fillColor = item.color;

                const strokeColor = layers.borders
                  ? isSelected
                    ? "var(--accent)"
                    : isDisputed
                    ? "var(--territory-disputed)"
                    : isDependent
                    ? "var(--territory-dependent)"
                    : "var(--territory-stroke)"
                  : "none";

                const strokeDasharray = layers.borders
                  ? isSelected
                    ? undefined
                    : isDisputed
                    ? "4 2.5"
                    : isDependent
                    ? "3.5 2"
                    : (item.properties.border_precision ?? 2) <= 1
                    ? "3.5 3.5"
                    : undefined
                  : undefined;

                const strokeWidth = isSelected
                  ? 1.8
                  : isDisputed
                  ? 0.95
                  : isDependent
                  ? 0.85
                  : 0.65;

                return (
                  <path
                    key={item.id}
                    d={item.path}
                    fill={fillColor}
                    fillRule="evenodd"
                    stroke={strokeColor}
                    strokeWidth={strokeWidth}
                    strokeDasharray={strokeDasharray}
                    vectorEffect="non-scaling-stroke"
                    className="transition-[fill-opacity] duration-150"
                    style={{
                      cursor: "pointer",
                      fillOpacity: isSelected ? 0.95 : isHovered ? 0.88 : "var(--territory-opacity)"
                    }}
                    onClick={(event) => selectFeature(event, item)}
                    onPointerEnter={(event) => {
                      if (dragRef.current.moved || suppressClickRef.current) return;
                      setHoveredId(item.id);
                      positionTooltip(event);
                    }}
                    onPointerMove={(event) => {
                      if (dragRef.current.active) return;
                      if (hoveredId === item.id) positionTooltip(event);
                    }}
                    onPointerLeave={() => {
                      if (!dragRef.current.active) setHoveredId(null);
                    }}
                  />
                );
              })}

              {hoveredFeature && hoveredFeature.id !== selectedId ? (
                <path
                  d={hoveredFeature.path}
                  fill="none"
                  stroke="var(--accent)"
                  strokeWidth="1.7"
                  vectorEffect="non-scaling-stroke"
                  pointerEvents="none"
                />
              ) : null}

              {selectedFeature ? (
                <path
                  d={selectedFeature.path}
                  fill="none"
                  stroke="var(--accent)"
                  strokeWidth="2.4"
                  vectorEffect="non-scaling-stroke"
                  pointerEvents="none"
                />
              ) : null}
            </g>
          </g>
        ) : null}

        <g ref={labelsGroupRef} pointerEvents="none" style={{ willChange: "transform" }}>
          {labels.map((label) => (
            <text
              key={label.id}
              x={label.x}
              y={label.y}
              textAnchor="middle"
              dominantBaseline="middle"
              fill={label.isSelected ? "var(--ink)" : "var(--label)"}
              fontSize={label.fontSize}
              fontWeight={label.isSelected ? 700 : 500}
              letterSpacing={label.letterSpacing}
              className="label-halo"
              style={{ fontFamily: "inherit" }}
            >
              {label.text}
            </text>
          ))}

          {userScreenPos ? (
            <g transform={`translate(${userScreenPos[0]} ${userScreenPos[1]})`}>
              <circle
                r={18}
                fill="var(--accent)"
                fillOpacity={0.22}
                className="animate-ping"
              />
              <circle
                r={13}
                fill="var(--accent)"
                fillOpacity={0.25}
              />
              <circle
                r={6.5}
                fill="var(--accent)"
                stroke="#ffffff"
                strokeWidth={2.2}
              />
              {userLocationLabel ? (
                <text
                  x={0}
                  y={-18}
                  textAnchor="middle"
                  fill="var(--ink)"
                  fontSize={11}
                  fontWeight={600}
                  className="label-halo"
                  style={{ fontFamily: "inherit" }}
                >
                  {userLocationLabel}
                </text>
              ) : null}
            </g>
          ) : null}
        </g>
      </svg>

      <div
        className="pointer-events-none absolute inset-0"
        style={{
          background: "radial-gradient(ellipse at 50% 42%, transparent 38%, var(--vignette) 100%)"
        }}
      />

      <div
        ref={tooltipRef}
        className={`pointer-events-none absolute left-0 top-0 z-30 w-[210px] rounded-2xl bg-search px-3 py-2.5 panel-shadow transition-opacity duration-100 ${
          hoveredFeature ? "opacity-100" : "opacity-0"
        }`}
        style={{ transform: "translate3d(var(--tip-x, -999px), var(--tip-y, -999px), 0)" }}
      >
        {hoveredFeature ? (
          <>
            <p className="truncate text-[12.5px] font-semibold text-ink">{hoveredFeature.name}</p>
            <p className="mt-0.5 text-[10.5px] text-muted">
              {typeLabel(hoveredFeature.type, lang)}
              {hoveredFeature.entity
                ? ` · ${formatSpan(hoveredFeature.entity.from_year, hoveredFeature.entity.to_year, lang)}`
                : ""}
            </p>
          </>
        ) : null}
      </div>

      {scaleBar ? (
        <div className="pointer-events-none absolute bottom-4 left-[29%] hidden -translate-x-1/2 items-end gap-2 text-[10px] font-medium text-muted sm:flex">
          <div className="relative h-2" style={{ width: Math.max(40, scaleBar.pixels) }}>
            <span className="absolute bottom-0 left-0 right-0 h-px bg-current" />
            <span className="absolute bottom-0 left-0 h-1.5 w-px bg-current" />
            <span className="absolute bottom-0 right-0 h-1.5 w-px bg-current" />
          </div>
          <span className="pb-0.5">{Math.round(scaleBar.km)} km</span>
        </div>
      ) : null}
        </>
      ) : null}
    </div>
  );
}
