"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Controls from "./Controls";
import DetailCard from "./DetailCard";
import EventPanel from "./EventPanel";
import { Icon, LogoMark } from "./Icons";
import Legend from "./Legend";
import MapCanvas from "./MapCanvas";
import SearchBox from "./SearchBox";
import Timeline from "./Timeline";
import { useKeyboardShortcuts } from "@/hooks/useKeyboardShortcuts";
import { useUrlState } from "@/hooks/useUrlState";
import {
  fetchCatalog,
  fetchEntityDetail,
  fetchLand,
  fetchLayer,
  getCachedLayer,
  prefetchAdjacentLayers
} from "@/lib/data";
import { clampView, fitView, zoomViewAt } from "@/lib/geo";
import { getInitialLang, getUI } from "@/lib/i18n";
import { nearestIndexForYear } from "@/lib/timeline";
import type {
  EntityDocument,
  EntityIndex,
  FeatureCollection,
  GeoFeature,
  GeoFeatureProperties,
  Lang,
  LayerToggles,
  MapSize,
  SourceRecord,
  StepMode,
  TabId,
  Theme,
  TimelineEntry,
  UserLocation,
  View
} from "@/lib/types";

const DESKTOP_BBOX: [number, number, number, number] = [-12, 14, 58, 64];
const MOBILE_BBOX: [number, number, number, number] = [-14, 14, 58, 64];
const INITIAL_YEAR = 100;

export default function Atlas() {
  const [lang, setLang] = useState<Lang>("en");
  const [theme, setTheme] = useState<Theme>("dark");
  const [timeline, setTimeline] = useState<TimelineEntry[]>([]);
  const [entities, setEntities] = useState<EntityIndex[]>([]);
  const [sources, setSources] = useState<SourceRecord[]>([]);
  const [land, setLand] = useState<FeatureCollection | null>(null);
  const [layer, setLayer] = useState<FeatureCollection | null>(null);
  const [index, setIndex] = useState(0);
  const [year, setYear] = useState(INITIAL_YEAR);
  const [month, setMonth] = useState<number | null>(null);
  const [stepMode, setStepMode] = useState<StepMode>("1y");
  const [userLocation, setUserLocation] = useState<UserLocation | null>(null);
  const [locating, setLocating] = useState(false);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [selectedProps, setSelectedProps] = useState<GeoFeatureProperties | null>(null);
  const [detail, setDetail] = useState<EntityDocument | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [loading, setLoading] = useState(true);
  const [layerLoading, setLayerLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(1);
  const [tab, setTab] = useState<TabId>("territories");
  const [view, setView] = useState<View | null>(null);
  const [mapSize, setMapSize] = useState<MapSize>({ width: 0, height: 0 });
  const [layers, setLayers] = useState<LayerToggles>({ labels: true, borders: true, graticule: true });
  const [sheetHeight, setSheetHeight] = useState(0);
  const [sheetEl, setSheetEl] = useState<HTMLElement | null>(null);
  const [themeReady, setThemeReady] = useState(false);

  const didAutoSelect = useRef(false);
  const urlInitRef = useRef<{
    year?: number;
    month?: number | null;
    selectedId?: string | null;
  }>({});
  const detailCache = useRef<Map<string, EntityDocument>>(new Map());

  const ui = getUI(lang);
  const currentLayer = timeline[index] || null;
  const compact = mapSize.width > 0 && mapSize.width < 640;

  const entitiesById = useMemo<Record<string, EntityIndex>>(
    () => Object.fromEntries(entities.map((item) => [item.id, item])),
    [entities]
  );
  const sourcesById = useMemo<Record<string, SourceRecord>>(
    () => Object.fromEntries(sources.map((item) => [item.id, item])),
    [sources]
  );

  useEffect(() => {
    const savedTheme = window.localStorage.getItem("hm-theme");
    if (savedTheme === "light" || savedTheme === "dark") setTheme(savedTheme);
    const initialLang = getInitialLang();
    if (initialLang) setLang(initialLang);
    setThemeReady(true);
  }, []);

  useEffect(() => {
    if (!themeReady) return;
    document.documentElement.dataset.theme = theme;
    window.localStorage.setItem("hm-theme", theme);
  }, [theme, themeReady]);

  useEffect(() => {
    document.documentElement.lang = lang;
    window.localStorage.setItem("hm-lang", lang);
  }, [lang]);

  const handleUrlInit = useCallback(
    (initial: {
      year?: number;
      month?: number | null;
      selectedId?: string | null;
      lang?: Lang;
    }) => {
      urlInitRef.current = initial;
      if (initial.lang) setLang(initial.lang);
      if (initial.year !== undefined) setYear(initial.year);
      if (initial.month !== undefined) {
        setMonth(initial.month);
        if (initial.month) setStepMode("month");
      }
      if (initial.selectedId) {
        didAutoSelect.current = true;
        setSelectedId(initial.selectedId);
      }
    },
    []
  );

  useUrlState({
    year,
    month,
    selectedId,
    lang,
    ready: !loading,
    onInit: handleUrlInit
  });

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    Promise.all([fetchCatalog(), fetchLand().catch(() => null)])
      .then(([catalog, landData]) => {
        if (cancelled) return;
        setTimeline(catalog.timeline || []);
        setEntities(catalog.entities || []);
        setSources(catalog.sources || []);
        setLand(landData);
        const startYear = urlInitRef.current.year ?? INITIAL_YEAR;
        const initialIndex = nearestIndexForYear(catalog.timeline || [], startYear);
        setIndex(initialIndex);
        if (urlInitRef.current.year === undefined) {
          setYear(catalog.timeline?.[initialIndex]?.year ?? INITIAL_YEAR);
        }
        setLoading(false);
      })
      .catch((caught: unknown) => {
        if (cancelled) return;
        setError(caught instanceof Error ? caught : new Error(String(caught)));
        setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!timeline.length) return undefined;
    const entry = timeline[index];
    if (!entry) return undefined;

    const cached = getCachedLayer(entry.year);
    if (cached) {
      setLayer(cached);
      setLayerLoading(false);
      prefetchAdjacentLayers(timeline, index);
      return undefined;
    }

    let cancelled = false;
    setLayerLoading(true);
    fetchLayer(entry)
      .then((data) => {
        if (cancelled) return;
        setLayer(data);
        setLayerLoading(false);
        setError(null);
        prefetchAdjacentLayers(timeline, index);
      })
      .catch((caught: unknown) => {
        if (cancelled) return;
        setLayer(null);
        setLayerLoading(false);
        setError(caught instanceof Error ? caught : new Error(String(caught)));
      });
    return () => {
      cancelled = true;
    };
  }, [index, timeline]);

  useEffect(() => {
    if (!layer || didAutoSelect.current) return;
    didAutoSelect.current = true;
    const roman = layer.features?.find(
      (feature) => feature.properties?.entity_id === "roman-empire"
    );
    if (roman) {
      setSelectedId("roman-empire");
      setSelectedProps(roman.properties ?? null);
    }
  }, [layer]);

  useEffect(() => {
    if (!selectedId) {
      setDetail(null);
      setDetailLoading(false);
      return undefined;
    }
    const cached = detailCache.current.get(selectedId);
    if (cached) {
      setDetail(cached);
      setDetailLoading(false);
      return undefined;
    }
    const item = entitiesById[selectedId];
    if (!item) {
      setDetail(null);
      return undefined;
    }
    let cancelled = false;
    setDetail(null);
    setDetailLoading(true);
    fetchEntityDetail(item)
      .then((document) => {
        detailCache.current.set(selectedId, document);
        if (cancelled) return;
        setDetail(document);
        setDetailLoading(false);
      })
      .catch(() => {
        if (cancelled) return;
        setDetail(null);
        setDetailLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [entitiesById, selectedId]);

  useEffect(() => {
    if (view || !mapSize.width || !mapSize.height) return;
    const bbox = mapSize.width < 640 ? MOBILE_BBOX : DESKTOP_BBOX;
    setView(fitView(bbox, mapSize.width, mapSize.height, 0.92));
  }, [mapSize, view]);

  useEffect(() => {
    if (!sheetEl) {
      setSheetHeight(0);
      return undefined;
    }
    const update = () => setSheetHeight(sheetEl.getBoundingClientRect().height);
    update();
    const observer = new ResizeObserver(update);
    observer.observe(sheetEl);
    return () => observer.disconnect();
  }, [sheetEl]);

  const handleYearMonthChange = useCallback(
    (nextYear: number, nextMonth: number | null) => {
      let clampedYear = Math.min(2026, Math.max(-3500, Math.round(nextYear)));
      if (clampedYear === 0) clampedYear = nextYear >= 0 ? 1 : -1;
      setYear(clampedYear);
      setMonth(nextMonth ? Math.min(12, Math.max(1, nextMonth)) : null);
      if (timeline.length) {
        setIndex(nearestIndexForYear(timeline, clampedYear, nextMonth));
      }
    },
    [timeline]
  );

  const handleIndexSelect = useCallback(
    (nextIndex: number) => {
      setIndex(nextIndex);
      if (timeline[nextIndex]) {
        setYear(timeline[nextIndex].year);
        setMonth(timeline[nextIndex].month ?? null);
      }
    },
    [timeline]
  );

  const handleStepPrev = useCallback(() => {
    if (!timeline.length) return;
    if (stepMode === "100y") {
      let nextYear = year - 100;
      if (year > 0 && nextYear <= 0) nextYear -= 1;
      handleYearMonthChange(Math.max(-3500, nextYear), null);
    } else if (stepMode === "10y") {
      let nextYear = year - 10;
      if (year > 0 && nextYear <= 0) nextYear -= 1;
      handleYearMonthChange(Math.max(-3500, nextYear), null);
    } else if (stepMode === "1y") {
      let nextYear = year - 1;
      if (nextYear === 0) nextYear = -1;
      handleYearMonthChange(Math.max(-3500, nextYear), null);
    } else if (stepMode === "month") {
      const currentMonth = month ?? 1;
      if (currentMonth > 1) {
        handleYearMonthChange(year, currentMonth - 1);
      } else if (year > -3500) {
        const prevYear = year - 1 === 0 ? -1 : year - 1;
        handleYearMonthChange(prevYear, 12);
      }
    }
  }, [handleYearMonthChange, month, stepMode, timeline.length, year]);

  const handleStepNext = useCallback(() => {
    if (!timeline.length) return;
    if (stepMode === "100y") {
      let nextYear = year + 100;
      if (year < 0 && nextYear >= 0) nextYear += 1;
      handleYearMonthChange(Math.min(2026, nextYear), null);
    } else if (stepMode === "10y") {
      let nextYear = year + 10;
      if (year < 0 && nextYear >= 0) nextYear += 1;
      handleYearMonthChange(Math.min(2026, nextYear), null);
    } else if (stepMode === "1y") {
      let nextYear = year + 1;
      if (nextYear === 0) nextYear = 1;
      handleYearMonthChange(Math.min(2026, nextYear), null);
    } else if (stepMode === "month") {
      const currentMonth = month ?? 1;
      if (currentMonth < 12) {
        handleYearMonthChange(year, currentMonth + 1);
      } else if (year < 2026) {
        const nextYear = year + 1 === 0 ? 1 : year + 1;
        handleYearMonthChange(nextYear, 1);
      }
    }
  }, [handleYearMonthChange, month, stepMode, timeline.length, year]);

  useEffect(() => {
    if (!playing || timeline.length < 2) return undefined;
    const baseMs = stepMode === "month" || stepMode === "1y" ? 700 : 1800;
    const timer = window.setInterval(() => {
      if (year >= 2026 && (stepMode !== "month" || (month ?? 1) >= 12)) {
        handleYearMonthChange(-3500, stepMode === "month" ? 1 : null);
      } else {
        handleStepNext();
      }
    }, Math.max(200, baseMs / speed));
    return () => window.clearInterval(timer);
  }, [handleStepNext, handleYearMonthChange, month, playing, speed, stepMode, timeline.length, year]);

  const handleSelect = useCallback((id: string, properties: GeoFeatureProperties | null) => {
    setSelectedId(id);
    setSelectedProps(properties);
    setTab("territories");
  }, []);

  const handleClear = useCallback(() => {
    setSelectedId(null);
    setSelectedProps(null);
    setDetail(null);
  }, []);

  const handleSizeChange = useCallback((size: MapSize) => {
    setMapSize(size);
  }, []);

  const handleSearchSelect = useCallback(
    (item: EntityIndex) => {
      const currentYear = currentLayer?.year ?? INITIAL_YEAR;
      const timelineYears = new Set(timeline.map((entry) => entry.year));
      const observed: number[] =
        Array.isArray(item.observed_years) && item.observed_years.length
          ? item.observed_years
          : [item.from_year, item.to_year].filter(
              (year): year is number => typeof year === "number" && Number.isFinite(year)
            );
      const exact = observed.filter((year) => timelineYears.has(year));
      let targetYear = currentYear;
      if (exact.length) {
        targetYear = exact.reduce(
          (best, year) => (Math.abs(year - currentYear) < Math.abs(best - currentYear) ? year : best),
          exact[0]
        );
      } else if (observed.length) {
        targetYear = observed[0];
      }
      const nextIdx = nearestIndexForYear(timeline, targetYear);
      setIndex(nextIdx);
      setYear(timeline[nextIdx]?.year ?? targetYear);
      setMonth(null);
      setSelectedId(item.id);
      setSelectedProps(null);
      setTab("territories");
    },
    [currentLayer, timeline]
  );

  const zoomBy = useCallback(
    (factor: number) => {
      if (!mapSize.width || !mapSize.height) return;
      setView((current) =>
        current
          ? zoomViewAt(
              current,
              factor,
              mapSize.width / 2,
              mapSize.height / 2,
              mapSize.width,
              mapSize.height
            )
          : current
      );
    },
    [mapSize]
  );

  const locateCurrentPosition = useCallback(() => {
    const applyLocation = (lon: number, lat: number) => {
      setUserLocation({ lon, lat });
      setLocating(false);
      setView((current) =>
        clampView({
          lon,
          lat,
          zoom: Math.max(current?.zoom ?? 1, 5.5)
        })
      );
    };

    const applyFallbackLocation = () => {
      const tz =
        typeof Intl !== "undefined"
          ? Intl.DateTimeFormat().resolvedOptions().timeZone || ""
          : "";
      if (tz.includes("Ho_Chi_Minh") || tz.includes("Saigon") || lang === "vi") {
        applyLocation(105.8542, 21.0285);
      } else if (tz.startsWith("Asia/Tokyo")) {
        applyLocation(139.6917, 35.6895);
      } else if (tz.startsWith("America/")) {
        applyLocation(-74.006, 40.7128);
      } else if (tz.startsWith("Europe/")) {
        applyLocation(2.3522, 48.8566);
      } else {
        applyLocation(105.8542, 21.0285);
      }
    };

    if (typeof navigator !== "undefined" && navigator.geolocation) {
      setLocating(true);
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          applyLocation(pos.coords.longitude, pos.coords.latitude);
        },
        () => {
          applyFallbackLocation();
        },
        { enableHighAccuracy: true, timeout: 6000, maximumAge: 60000 }
      );
    } else {
      applyFallbackLocation();
    }
  }, [lang]);

  const toggleLayer = useCallback((key: keyof LayerToggles) => {
    setLayers((current) => ({ ...current, [key]: !current[key] }));
  }, []);

  useKeyboardShortcuts({
    onTogglePlay: () => setPlaying((current) => !current),
    onStepPrev: handleStepPrev,
    onStepNext: handleStepNext,
    onZoomIn: () => zoomBy(1.45),
    onZoomOut: () => zoomBy(1 / 1.45),
    onClearSelection: handleClear
  });

  const visibleLayer = useMemo<FeatureCollection | null>(() => {
    if (!layer) return null;
    if (tab !== "civilizations") return layer;
    return {
      ...layer,
      features: (layer.features || []).filter((feature) =>
        ["empire", "kingdom", "civilization"].includes(feature.properties?.type ?? "")
      )
    };
  }, [layer, tab]);

  const selectedIndexItem = selectedId ? entitiesById[selectedId] || selectedProps : null;
  const showEvents = tab === "events";
  const showDetail = !showEvents && Boolean(selectedId);
  const approximate = Boolean(
    (currentLayer as (TimelineEntry & { features?: GeoFeature[] }) | null)?.features?.some(
      (feature) => (feature.properties?.border_precision ?? 2) <= 1
    )
  );

  const tabs: Array<{ id: TabId; label: string }> = [
    { id: "territories", label: ui.territories },
    { id: "civilizations", label: ui.civilizations },
    { id: "events", label: ui.events }
  ];

  return (
    <div className="flex h-dvh w-full flex-col overflow-hidden bg-map text-ink">
      <main className="relative min-h-0 flex-1 overflow-hidden">
        <MapCanvas
          layer={visibleLayer}
          land={land}
          entitiesById={entitiesById}
          lang={lang}
          selectedId={selectedId}
          onSelect={handleSelect}
          onClear={handleClear}
          view={view}
          setView={setView}
          onSizeChange={handleSizeChange}
          layers={layers}
          userLocation={userLocation}
          userLocationLabel={ui.currentLocation}
        />

        <header className="absolute left-3 top-3 z-40 sm:left-5 sm:top-5">
          <div className="hidden items-center gap-2 text-ink drop-shadow-[0_2px_10px_rgba(0,0,0,0.24)] sm:flex">
            <LogoMark size={22} />
            <div>
              <h1 className="text-[18px] font-semibold leading-none tracking-[-0.02em]">
                {ui.appTitle}
              </h1>
              <p className="mt-0.5 text-[7.5px] font-semibold uppercase tracking-[0.2em] text-muted">
                {ui.appSubtitle}
              </p>
            </div>
          </div>

          <SearchBox
            entities={entities}
            lang={lang}
            ui={ui}
            onSelect={handleSearchSelect}
            compact={compact}
            className="w-[calc(100vw-68px)] max-w-[330px] sm:mt-2 sm:w-[330px]"
          />

          <div className="mt-2 flex items-center gap-2">
            {tabs.map((item) => {
              const active = tab === item.id;
              return (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => {
                    setTab(item.id);
                    if (item.id === "events") setPlaying(false);
                  }}
                  className={`flex h-8 items-center gap-1.5 rounded-xl px-3 text-[11.5px] font-medium transition ${
                    active
                      ? "bg-tab-active text-ink shadow-sm"
                      : "bg-tab text-muted hover:text-ink"
                  }`}
                >
                  {active ? (
                    <Icon name="check" size={16} className="text-ink" />
                  ) : null}
                  {item.label}
                </button>
              );
            })}
          </div>
        </header>

        <Controls
          theme={theme}
          onToggleTheme={() => setTheme((current) => (current === "dark" ? "light" : "dark"))}
          onZoomIn={() => zoomBy(1.45)}
          onZoomOut={() => zoomBy(1 / 1.45)}
          onReset={locateCurrentPosition}
          locating={locating}
          hasUserLocation={Boolean(userLocation)}
          layers={layers}
          onToggleLayer={toggleLayer}
          lang={lang}
          onToggleLang={setLang}
          ui={ui}
        />

        {showEvents ? (
          <>
            <div className="absolute left-5 top-[148px] z-30 hidden sm:block">
              <EventPanel
                timeline={timeline}
                lang={lang}
                ui={ui}
                index={index}
                setIndex={handleIndexSelect}
                onClose={() => setTab("territories")}
              />
            </div>
            <div
              ref={setSheetEl}
              className="absolute bottom-0 left-0 right-0 z-30 pointer-events-none sm:hidden"
            >
              <EventPanel
                timeline={timeline}
                lang={lang}
                ui={ui}
                index={index}
                setIndex={handleIndexSelect}
                onClose={() => setTab("territories")}
                variant="sheet"
              />
            </div>
          </>
        ) : null}

        {showDetail ? (
          <>
            <div className="absolute left-5 top-[148px] z-30 hidden sm:block">
              <DetailCard
                detail={detail}
                indexItem={selectedIndexItem}
                sourcesById={sourcesById}
                lang={lang}
                ui={ui}
                onClose={handleClear}
                year={year}
                month={month}
              />
            </div>
            <div
              ref={setSheetEl}
              className="absolute bottom-0 left-0 right-0 z-30 pointer-events-none sm:hidden"
            >
              <DetailCard
                detail={detail}
                indexItem={selectedIndexItem}
                sourcesById={sourcesById}
                lang={lang}
                ui={ui}
                onClose={handleClear}
                year={year}
                month={month}
                variant="sheet"
              />
            </div>
          </>
        ) : null}

        <Legend
          layer={visibleLayer}
          entitiesById={entitiesById}
          lang={lang}
          ui={ui}
          year={year}
          view={view}
          size={mapSize}
          className="absolute z-20"
          style={{
            left: compact ? 12 : undefined,
            right: compact ? undefined : 20,
            bottom: compact ? (sheetHeight ? sheetHeight + 10 : 12) : 24
          }}
        />

        <div className="pointer-events-none absolute bottom-2.5 right-6 z-10 hidden text-right text-[10px] font-medium text-muted sm:block">
          {ui.regional} · {approximate ? ui.approximateShort : ui.boundaryGeoreferenced} ·{" "}
          {ui.attribution}
        </div>

        {loading || layerLoading ? (
          <div className="pointer-events-none absolute inset-0 z-20 grid place-items-center">
            <div className="flex items-center gap-2.5 rounded-full bg-search px-4 py-2 text-[11px] font-medium text-muted panel-shadow">
              <span className="size-3 animate-spin rounded-full border-2 border-accent border-t-transparent" />
              {ui.loading}
            </div>
          </div>
        ) : null}

        {error && !loading ? (
          <div className="absolute left-1/2 top-1/2 z-50 w-[min(92vw,360px)] -translate-x-1/2 -translate-y-1/2 rounded-2xl border border-line bg-panel p-5 text-center panel-shadow backdrop-blur-xl">
            <p className="text-[14px] font-semibold text-ink">{ui.error}</p>
            <p className="mt-1.5 text-[11px] leading-snug text-muted">
              {error.message}
            </p>
            <button
              type="button"
              onClick={() => window.location.reload()}
              className="mt-4 rounded-xl bg-accent px-4 py-2 text-[11.5px] font-semibold text-accent-ink transition hover:brightness-105"
            >
              {ui.retry}
            </button>
          </div>
        ) : null}
      </main>

      <Timeline
        timeline={timeline}
        index={index}
        year={year}
        month={month}
        stepMode={stepMode}
        setStepMode={setStepMode}
        onYearMonthChange={handleYearMonthChange}
        onStepPrev={handleStepPrev}
        onStepNext={handleStepNext}
        lang={lang}
        ui={ui}
        playing={playing}
        onTogglePlay={() => setPlaying((current) => !current)}
        speed={speed}
        setSpeed={setSpeed}
      />
    </div>
  );
}
