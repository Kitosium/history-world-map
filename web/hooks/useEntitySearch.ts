"use client";

import { useMemo } from "react";
import { localizedName, normalizeText } from "@/lib/format";
import type { EntityIndex, Lang } from "@/lib/types";

interface IndexedEntity {
  item: EntityIndex;
  normEn: string;
  normVi: string;
  normId: string;
  haystack: string[];
}

export function useEntitySearch(entities: EntityIndex[], query: string, lang: Lang) {
  const index = useMemo<IndexedEntity[]>(() => {
    return entities.map((item) => {
      const normEn = normalizeText(item.name_en);
      const normVi = normalizeText(item.name_vi);
      const normId = normalizeText(item.id);
      const extraNames = item.names
        ? Object.values(item.names)
            .filter((val): val is string => typeof val === "string")
            .map(normalizeText)
        : [];
      return {
        item,
        normEn,
        normVi,
        normId,
        haystack: [normEn, normVi, normId, ...extraNames].filter(Boolean)
      };
    });
  }, [entities]);

  return useMemo<EntityIndex[]>(() => {
    const needle = normalizeText(query);
    if (needle.length < 2) return [];

    const matches: Array<{ entry: IndexedEntity; score: number }> = [];
    for (let i = 0; i < index.length; i += 1) {
      const entry = index[i];
      if (entry.haystack.some((value) => value.includes(needle))) {
        const primary = normalizeText(localizedName(entry.item, lang)) || entry.normEn || entry.normVi;
        const score = primary === needle ? 0 : primary.startsWith(needle) ? 1 : 2;
        matches.push({ entry, score });
        if (matches.length >= 48) break;
      }
    }

    return matches
      .sort((a, b) => {
        if (a.score !== b.score) return a.score - b.score;
        return localizedName(a.entry.item, lang).localeCompare(localizedName(b.entry.item, lang));
      })
      .slice(0, 8)
      .map((m) => m.entry.item);
  }, [index, lang, query]);
}
