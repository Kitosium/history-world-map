import type { Lang, TimelineEntry } from "@/lib/types";

export const MIN_YEAR = -3500;
export const MAX_YEAR = 2026;

export interface HistoricalPeriod {
  id: string;
  from: number;
  to: number;
  bandFrom: number;
  bandTo: number;
  vi: string;
  en: string;
  short_vi: string;
  short_en: string;
  range_vi: string;
  range_en: string;
  inMapRange: boolean;
  [key: string]: unknown;
}

export interface EraBand {
  id: string;
  from: number;
  to: number;
  jumpYear: number;
  en: string;
  vi: string;
  short_en: string;
  short_vi: string;
  range_en: string;
  range_vi: string;
  [key: string]: unknown;
}

export interface EventMarker {
  index: number;
  item: TimelineEntry;
  fraction: number;
}

export const HISTORICAL_PERIODS: HistoricalPeriod[] = [
  {
    id: "prehistory",
    from: -3300000,
    to: -3000,
    bandFrom: -3500,
    bandTo: -3000,
    vi: "Thời kỳ Tiền sử",
    en: "Prehistory",
    short_vi: "Tiền sử",
    short_en: "Prehistory",
    range_vi: "~3,3 tr. TCN – 3000 TCN",
    range_en: "~3.3M BCE – 3000 BCE",
    inMapRange: true
  },
  {
    id: "ancient_history",
    from: -3000,
    to: 476,
    bandFrom: -3000,
    bandTo: 476,
    vi: "Thời kỳ Cổ đại",
    en: "Ancient History",
    short_vi: "Cổ đại",
    short_en: "Ancient",
    range_vi: "3000 TCN – 476",
    range_en: "3000 BCE – 476 CE",
    inMapRange: true
  },
  {
    id: "middle_ages",
    from: 476,
    to: 1492,
    bandFrom: 476,
    bandTo: 1492,
    vi: "Thời kỳ Trung đại",
    en: "Middle Ages",
    short_vi: "Trung đại",
    short_en: "Middle Ages",
    range_vi: "476 – 1492",
    range_en: "476 – 1492",
    inMapRange: true
  },
  {
    id: "early_modern",
    from: 1492,
    to: 1914,
    bandFrom: 1492,
    bandTo: 1914,
    vi: "Thời kỳ Cận đại",
    en: "Early Modern Period",
    short_vi: "Cận đại",
    short_en: "Early Modern",
    range_vi: "1492 – 1914",
    range_en: "1492 – 1914",
    inMapRange: true
  },
  {
    id: "world_war_1",
    from: 1914,
    to: 1918,
    bandFrom: 1914,
    bandTo: 1918,
    vi: "Chiến tranh Thế giới thứ nhất",
    en: "World War I",
    short_vi: "CTTG I",
    short_en: "WWI",
    range_vi: "1914 – 1918",
    range_en: "1914 – 1918",
    inMapRange: true
  },
  {
    id: "interwar",
    from: 1918,
    to: 1939,
    bandFrom: 1918,
    bandTo: 1939,
    vi: "Giai đoạn Giữa hai cuộc thế chiến",
    en: "Interwar Period",
    short_vi: "Giữa hai thế chiến",
    short_en: "Interwar",
    range_vi: "1918 – 1939",
    range_en: "1918 – 1939",
    inMapRange: true
  },
  {
    id: "world_war_2",
    from: 1939,
    to: 1945,
    bandFrom: 1939,
    bandTo: 1947,
    vi: "Chiến tranh Thế giới thứ hai",
    en: "World War II",
    short_vi: "CTTG II",
    short_en: "WWII",
    range_vi: "1939 – 1945",
    range_en: "1939 – 1945",
    inMapRange: true
  },
  {
    id: "cold_war",
    from: 1947,
    to: 1991,
    bandFrom: 1947,
    bandTo: 1991,
    vi: "Thời kỳ Chiến tranh Lạnh",
    en: "Cold War Era",
    short_vi: "Chiến tranh Lạnh",
    short_en: "Cold War",
    range_vi: "1947 – 1991",
    range_en: "1947 – 1991",
    inMapRange: true
  },
  {
    id: "modern",
    from: 1991,
    to: 2026,
    bandFrom: 1991,
    bandTo: 2026,
    vi: "Thời kỳ Hiện đại",
    en: "Contemporary Period",
    short_vi: "Hiện đại",
    short_en: "Modern",
    range_vi: "1991 – nay",
    range_en: "1991 – present",
    inMapRange: true
  }
];

// spacing allocation to avoid label collision between 1991 and 2026
export const TIMELINE_STOPS: ReadonlyArray<readonly [number, number]> = [
  [-3500, 0],
  [-3000, 0.07],
  [-1500, 0.16],
  [-1, 0.25],
  [476, 0.31],
  [1000, 0.38],
  [1492, 0.45],
  [1800, 0.52],
  [1914, 0.58],
  [1918, 0.645],
  [1939, 0.71],
  [1945, 0.775],
  [1947, 0.785],
  [1991, 0.865],
  [2026, 1]
];

export const ERA_BANDS: EraBand[] = HISTORICAL_PERIODS.filter((p) => p.inMapRange).map((p) => ({
  id: p.id,
  from: p.bandFrom,
  to: p.bandTo,
  jumpYear: Math.max(MIN_YEAR, p.from),
  en: p.en,
  vi: p.vi,
  short_en: p.short_en,
  short_vi: p.short_vi,
  range_en: p.range_en,
  range_vi: p.range_vi
}));

export const TICK_YEARS: number[] = [-3500, 476, 1492, 1914, 1945, 2026];

export function getPeriodForYear(year: number): HistoricalPeriod {
  if (year < -3000) return HISTORICAL_PERIODS[0];
  if (year < 476) return HISTORICAL_PERIODS[1];
  if (year < 1492) return HISTORICAL_PERIODS[2];
  if (year < 1914) return HISTORICAL_PERIODS[3];
  if (year < 1918) return HISTORICAL_PERIODS[4];
  if (year < 1939) return HISTORICAL_PERIODS[5];
  if (year < 1947) return HISTORICAL_PERIODS[6];
  if (year < 1991) return HISTORICAL_PERIODS[7];
  return HISTORICAL_PERIODS[8];
}

export function getPeriodName(period: HistoricalPeriod | EraBand | Record<string, unknown>, lang: string = "en"): string {
  const direct = (period as Record<string, unknown>)[lang];
  if (typeof direct === "string" && direct) return direct;
  return ((period as Record<string, unknown>).en || (period as Record<string, unknown>).vi || "") as string;
}

export function getPeriodRange(period: HistoricalPeriod | EraBand | Record<string, unknown>, lang: string = "en"): string {
  const direct = (period as Record<string, unknown>)[`range_${lang}`];
  if (typeof direct === "string" && direct) return direct;
  return ((period as Record<string, unknown>).range_en || (period as Record<string, unknown>).range_vi || "") as string;
}

export function getPeriodShort(period: HistoricalPeriod | EraBand | Record<string, unknown>, lang: string = "en"): string {
  const direct = (period as Record<string, unknown>)[`short_${lang}`];
  if (typeof direct === "string" && direct) return direct;
  return ((period as Record<string, unknown>).short_en || (period as Record<string, unknown>).short_vi || "") as string;
}

export function formatPeriodLabel(year: number, lang: Lang, includeRange = false): string {
  const period = getPeriodForYear(year);
  const name = getPeriodName(period, lang);
  if (!includeRange) return name;
  const range = getPeriodRange(period, lang);
  return `${name} (${range})`;
}

export function yearToFraction(year: number) {
  const value = Number(year);
  if (!Number.isFinite(value)) return 0;
  if (value <= TIMELINE_STOPS[0][0]) return 0;
  if (value >= TIMELINE_STOPS[TIMELINE_STOPS.length - 1][0]) return 1;
  for (let i = 1; i < TIMELINE_STOPS.length; i += 1) {
    const [rightYear, rightFraction] = TIMELINE_STOPS[i];
    const [leftYear, leftFraction] = TIMELINE_STOPS[i - 1];
    if (value <= rightYear) {
      const ratio = (value - leftYear) / (rightYear - leftYear);
      return leftFraction + ratio * (rightFraction - leftFraction);
    }
  }
  return 1;
}

export function fractionToYear(fraction: number) {
  const value = Math.min(1, Math.max(0, Number(fraction) || 0));
  for (let i = 1; i < TIMELINE_STOPS.length; i += 1) {
    const [rightYear, rightFraction] = TIMELINE_STOPS[i];
    const [leftYear, leftFraction] = TIMELINE_STOPS[i - 1];
    if (value <= rightFraction) {
      const ratio = (value - leftFraction) / Math.max(1e-9, rightFraction - leftFraction);
      return leftYear + ratio * (rightYear - leftYear);
    }
  }
  return TIMELINE_STOPS[TIMELINE_STOPS.length - 1][0];
}

export function nearestIndexForYear(
  timeline: TimelineEntry[],
  year: number,
  month?: number | null
) {
  if (!timeline?.length) return 0;
  const effectiveTarget = year + (month ? (month - 1) / 12 : 0);
  const target = yearToFraction(effectiveTarget);
  let bestIndex = 0;
  let bestDistance = Infinity;
  timeline.forEach((item, index) => {
    const itemEffective = item.year + (item.month ? (item.month - 1) / 12 : 0);
    const distance = Math.abs(yearToFraction(itemEffective) - target);
    if (distance < bestDistance) {
      bestDistance = distance;
      bestIndex = index;
    }
  });
  return bestIndex;
}

export function nearestIndexForFraction(timeline: TimelineEntry[], fraction: number) {
  if (!timeline?.length) return 0;
  const target = Math.min(1, Math.max(0, fraction));
  let bestIndex = 0;
  let bestDistance = Infinity;
  timeline.forEach((item, index) => {
    const distance = Math.abs(yearToFraction(item.year) - target);
    if (distance < bestDistance) {
      bestDistance = distance;
      bestIndex = index;
    }
  });
  return bestIndex;
}

export function pickEventMarkers(timeline: TimelineEntry[], currentIndex: number): EventMarker[] {
  if (!timeline?.length) return [];
  const chosen = new Set<number>();
  const targets = [0.02, 0.25, 0.5, 0.75, 1];
  for (const target of targets) {
    chosen.add(nearestIndexForFraction(timeline, target));
  }
  chosen.add(currentIndex);
  return [...chosen]
    .sort((a, b) => a - b)
    .map((index) => ({
      index,
      item: timeline[index],
      fraction: yearToFraction(timeline[index].year)
    }));
}

export function parseYearInput(text: string) {
  const normalized = String(text || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase();
  const match = normalized.match(/-?\d+/);
  if (!match) return null;
  let year = Number.parseInt(match[0], 10);
  if (!Number.isFinite(year)) return null;
  if (normalized.includes("bce") || normalized.includes("tcn") || normalized.includes("bc")) {
    year = -Math.abs(year);
  } else if (normalized.includes("ce") || normalized.includes("scn") || normalized.includes("ad")) {
    year = Math.abs(year);
  }
  return year;
}
