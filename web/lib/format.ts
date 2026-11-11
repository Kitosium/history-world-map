import type {
  EntityLike,
  Lang,
  SourceRecord,
  TimelineEntry
} from "@/lib/types";
import { getLocale } from "@/lib/i18n";

function nameMap(item: EntityLike): Record<string, unknown> {
  const raw = item.names;
  if (raw && typeof raw === "object") {
    const canonical = (raw as Record<string, unknown>).canonical;
    if (canonical && typeof canonical === "object") {
      return canonical as Record<string, unknown>;
    }
    return raw as Record<string, unknown>;
  }
  return {};
}

export function formatYear(year: number | null | undefined, lang: Lang = "en") {
  if (year === null || year === undefined || Number.isNaN(year)) return "—";
  const value = Number(year);
  const locale = getLocale(lang);
  if (value < 0) return `${Math.abs(value)} ${locale.bceSuffix}`;
  if (value === 0) return `1 ${locale.bceSuffix}`;
  return `${value} ${locale.ceSuffix}`;
}

export function yearParts(year: number | null | undefined, lang: Lang = "en") {
  if (year === null || year === undefined || Number.isNaN(year)) {
    return { number: "—", suffix: "" };
  }
  const value = Number(year);
  const locale = getLocale(lang);
  if (value < 0) return { number: String(Math.abs(value)), suffix: locale.bceSuffix };
  if (value === 0) return { number: "1", suffix: locale.bceSuffix };
  return { number: String(value), suffix: locale.ceSuffix };
}

export function formatYearMonth(
  year: number | null | undefined,
  month: number | null | undefined,
  lang: Lang = "en"
) {
  if (year === null || year === undefined || Number.isNaN(year)) return "—";
  if (!month || month < 1 || month > 12) return formatYear(year, lang);
  const yearStr = formatYear(year, lang);
  return getLocale(lang).formatMonthYear(month, yearStr);
}

export function formatDatePoint(
  year: number | null | undefined,
  month: number | null | undefined,
  day: number | null | undefined,
  precision: string | null | undefined,
  lang: Lang = "en"
) {
  if (year === null || year === undefined || Number.isNaN(year)) return "—";
  const yearStr = formatYear(year, lang);
  if (precision === "day" && day && month) {
    return getLocale(lang).formatFullDate(day, month, yearStr);
  }
  if ((precision === "month" || month) && month) {
    return formatYearMonth(year, month, lang);
  }
  return yearStr;
}

export function formatDetailedSpan(
  fromYear: number | null | undefined,
  fromMonth: number | null | undefined,
  fromDay: number | null | undefined,
  toYear: number | null | undefined,
  toMonth: number | null | undefined,
  toDay: number | null | undefined,
  lang: Lang = "en",
  status?: string
) {
  if (fromYear === null || fromYear === undefined) return "—";
  const fromStr = formatDatePoint(
    fromYear,
    fromMonth,
    fromDay,
    fromDay ? "day" : fromMonth ? "month" : "year",
    lang
  );
  if (status === "active" || (toYear !== null && toYear !== undefined && toYear >= 2026)) {
    return `${fromStr} – ${getLocale(lang).presentLabel}`;
  }
  if (toYear === null || toYear === undefined || (toYear === fromYear && !toMonth && !toDay)) {
    return fromStr;
  }
  const toStr = formatDatePoint(
    toYear,
    toMonth,
    toDay,
    toDay ? "day" : toMonth ? "month" : "year",
    lang
  );
  return `${fromStr} – ${toStr}`;
}

export function formatSpan(
  from: number | null | undefined,
  to: number | null | undefined,
  lang: Lang = "en"
) {
  if (from === null || from === undefined) return "—";
  if (to === null || to === undefined || to === from) return formatYear(from, lang);
  return `${formatYear(from, lang)} – ${formatYear(to, lang)}`;
}

export function localizedName(item: EntityLike | null | undefined, lang: Lang = "en") {
  if (!item) return "—";
  const names = nameMap(item);
  const direct = names[lang] || item[`name_${lang}`];
  if (typeof direct === "string" && direct) return direct;
  // fallback gracefully to available names
  const fallback = item.name_en || item.name_vi || names.en || names.vi || Object.values(names)[0] || item.id || "—";
  return typeof fallback === "string" ? fallback : "—";
}

export function secondaryName(item: EntityLike | null | undefined, lang: Lang = "en") {
  if (!item) return "";
  const primary = localizedName(item, lang);
  const names = nameMap(item);
  for (const altLang of ["en", "vi", "zh", "fr", "es", "ja", "de", "ru"]) {
    if (altLang === lang) continue;
    const candidate = item[`name_${altLang}`] || names[altLang];
    if (typeof candidate === "string" && candidate && candidate !== primary) {
      return candidate;
    }
  }
  return "";
}

export function localizedDescription(item: EntityLike | null | undefined, lang: Lang = "en") {
  if (!item) return "";
  const direct = item[`description_${lang}`] || item.descriptions?.[lang];
  if (typeof direct === "string" && direct) return direct;
  return item.description_en || item.descriptions?.en || item.description_vi || item.descriptions?.vi || "";
}

export function localizedEra(layer: TimelineEntry | null | undefined, lang: Lang = "en") {
  if (!layer) return "";
  const direct = layer[`era_${lang}` as keyof TimelineEntry];
  if (typeof direct === "string" && direct) return direct;
  return layer.era_en || layer.era_vi || "";
}

export function localizedEvent(layer: TimelineEntry | null | undefined, lang: Lang = "en") {
  if (!layer) return "";
  const direct = layer[`event_name_${lang}` as keyof TimelineEntry];
  if (typeof direct === "string" && direct) return direct;
  return layer.event_name_en || layer.event_name_vi || "";
}

export function normalizeText(value: unknown) {
  return String(value || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .trim();
}

export function sourceTitle(source: SourceRecord | null | undefined, lang: Lang = "en") {
  if (!source) return "—";
  const title = source.title;
  if (title && typeof title === "object") {
    return title[lang] || title.en || title.vi || source.title_en || source.title_vi || source.id || "—";
  }
  return source.title_en || source.title_vi || source.id || "—";
}

export function confidenceLabel(value: string | null | undefined, lang: Lang = "en") {
  const labels: Record<Lang, Record<string, string>> = {
    en: { high: "High", medium: "Medium", low: "Low" },
    vi: { high: "Cao", medium: "Trung bình", low: "Thấp" }
  };
  return (value && labels[lang]?.[value]) || (value && labels.en[value]) || value || "—";
}

export function truncate(value: unknown, length = 42) {
  const text = String(value || "");
  return text.length > length ? `${text.slice(0, length - 1).trim()}…` : text;
}
