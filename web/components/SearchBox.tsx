"use client";

import { useEffect, useRef, useState } from "react";
import type { KeyboardEvent } from "react";
import { Icon } from "./Icons";
import { useEntitySearch } from "@/hooks/useEntitySearch";
import { formatSpan, localizedName, secondaryName } from "@/lib/format";
import { typeLabel } from "@/lib/i18n";
import type { EntityIndex, Lang, UILabels } from "@/lib/types";

interface SearchBoxProps {
  entities: EntityIndex[];
  lang: Lang;
  ui: UILabels;
  onSelect: (item: EntityIndex) => void;
  compact?: boolean;
  className?: string;
}

export default function SearchBox({
  entities,
  lang,
  ui,
  onSelect,
  compact = false,
  className = ""
}: SearchBoxProps) {
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(0);
  const containerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const results = useEntitySearch(entities, query, lang);

  useEffect(() => {
    setActiveIndex(0);
  }, [query]);

  useEffect(() => {
    function handlePointerDown(event: PointerEvent) {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("pointerdown", handlePointerDown);
    return () => document.removeEventListener("pointerdown", handlePointerDown);
  }, []);

  function choose(item: EntityIndex) {
    setQuery(localizedName(item, lang));
    setOpen(false);
    onSelect(item);
    inputRef.current?.blur();
  }

  function handleKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === "Escape") {
      setOpen(false);
      inputRef.current?.blur();
      return;
    }
    if (!open || results.length === 0) return;
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setActiveIndex((index) => (index + 1) % results.length);
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setActiveIndex((index) => (index - 1 + results.length) % results.length);
    } else if (event.key === "Enter") {
      event.preventDefault();
      choose(results[activeIndex] || results[0]);
    }
  }

  const showResults = open && query.trim().length >= 2;

  return (
    <div ref={containerRef} className={`relative ${className}`}>
      <div className="flex h-11 items-center gap-2.5 rounded-2xl bg-search px-3.5 transition focus-within:ring-2 focus-within:ring-accent/40 sm:h-11">
        <Icon name="search" size={20} className="text-muted" />
        <input
          ref={inputRef}
          data-atlas-search="true"
          value={query}
          onChange={(event) => {
            setQuery(event.target.value);
            setOpen(true);
          }}
          onFocus={() => setOpen(true)}
          onKeyDown={handleKeyDown}
          placeholder={compact ? ui.searchPlaceholderCompact : ui.searchPlaceholder}
          aria-label={ui.searchPlaceholder}
          autoComplete="off"
          spellCheck={false}
          className="min-w-0 flex-1 bg-transparent text-[13.5px] font-medium text-ink outline-none placeholder:text-muted"
        />
        {query ? (
          <button
            type="button"
            onClick={() => {
              setQuery("");
              setOpen(false);
              inputRef.current?.focus();
            }}
            aria-label={ui.close}
            className="grid size-6 place-items-center rounded-full text-muted transition hover:bg-panel-2 hover:text-ink"
          >
            <Icon name="close" size={18} />
          </button>
        ) : null}
      </div>

      {showResults ? (
        <div className="pop-in absolute left-0 right-0 top-[calc(100%+8px)] z-50 overflow-hidden rounded-2xl bg-search p-1.5 panel-shadow">
          {results.length === 0 ? (
            <div className="px-3 py-4 text-sm text-muted">{ui.noResults}</div>
          ) : (
            <div className="max-h-[340px] overflow-y-auto thin-scrollbar">
              {results.map((item, index) => {
                const name = localizedName(item, lang);
                const secondary = secondaryName(item, lang);
                return (
                  <button
                    key={item.id}
                    type="button"
                    onPointerDown={(event) => event.preventDefault()}
                    onClick={() => choose(item)}
                    onMouseEnter={() => setActiveIndex(index)}
                    className={`flex w-full items-start gap-3 rounded-xl px-3 py-2.5 text-left transition ${
                      index === activeIndex ? "bg-control" : "hover:bg-control/70"
                    }`}
                  >
                    <span className="mt-1 grid size-7 shrink-0 place-items-center rounded-lg bg-accent-soft text-accent">
                      <Icon name="globe" size={18} />
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-[13.5px] font-semibold text-ink">
                        {name}
                        {secondary ? (
                          <span className="ml-1.5 font-normal text-muted">({secondary})</span>
                        ) : null}
                      </span>
                      <span className="mt-0.5 flex flex-wrap items-center gap-x-2 gap-y-0.5 text-[11px] text-muted">
                        <span className="capitalize">{typeLabel(item.type, lang)}</span>
                        <span className="size-1 rounded-full bg-faint/60" />
                        <span>{formatSpan(item.from_year, item.to_year, lang)}</span>
                      </span>
                    </span>
                  </button>
                );
              })}
            </div>
          )}
        </div>
      ) : null}
    </div>
  );
}
