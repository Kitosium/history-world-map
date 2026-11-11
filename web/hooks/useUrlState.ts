"use client";

import { useEffect, useRef } from "react";
import type { Lang } from "@/lib/types";

interface UrlStateParams {
  year: number;
  month: number | null;
  selectedId: string | null;
  lang: Lang;
  ready: boolean;
  onInit: (initial: {
    year?: number;
    month?: number | null;
    selectedId?: string | null;
    lang?: Lang;
  }) => void;
}

export function useUrlState({
  year,
  month,
  selectedId,
  lang,
  ready,
  onInit
}: UrlStateParams) {
  const didReadRef = useRef(false);

  useEffect(() => {
    if (didReadRef.current || typeof window === "undefined") return;
    didReadRef.current = true;
    const params = new URLSearchParams(window.location.search);
    const rawYear = params.get("year");
    const rawMonth = params.get("month");
    const rawEntity = params.get("entity");
    const rawLang = params.get("lang");

    const parsedYear = rawYear !== null ? Number.parseInt(rawYear, 10) : undefined;
    const parsedMonth = rawMonth !== null ? Number.parseInt(rawMonth, 10) : undefined;

    onInit({
      year:
        parsedYear !== undefined && Number.isFinite(parsedYear)
          ? Math.min(2026, Math.max(-3500, parsedYear))
          : undefined,
      month:
        parsedMonth !== undefined && Number.isFinite(parsedMonth)
          ? Math.min(12, Math.max(1, parsedMonth))
          : null,
      selectedId: rawEntity || undefined,
      lang: rawLang === "vi" || rawLang === "en" ? rawLang : undefined
    });
  }, [onInit]);

  useEffect(() => {
    if (!ready || typeof window === "undefined") return;
    const params = new URLSearchParams(window.location.search);
    params.set("year", String(year));
    if (month) {
      params.set("month", String(month));
    } else {
      params.delete("month");
    }
    if (selectedId) {
      params.set("entity", selectedId);
    } else {
      params.delete("entity");
    }
    params.set("lang", lang);

    const nextSearch = `?${params.toString()}`;
    if (window.location.search !== nextSearch) {
      window.history.replaceState(null, "", `${window.location.pathname}${nextSearch}`);
    }
  }, [lang, month, ready, selectedId, year]);
}
