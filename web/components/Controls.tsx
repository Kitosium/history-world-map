"use client";

import { useEffect, useRef, useState } from "react";
import type { ReactNode } from "react";
import { Icon } from "./Icons";
import type { Lang, LayerToggles, Theme, UILabels } from "@/lib/types";
import { SUPPORTED_LANGUAGES } from "@/lib/i18n";

function ControlButton({
  label,
  onClick,
  active = false,
  size = "md",
  shape = "square",
  children,
  className = ""
}: {
  label: string;
  onClick: () => void;
  active?: boolean;
  size?: "sm" | "md";
  shape?: "square" | "circle";
  children: ReactNode;
  className?: string;
}) {
  const sizing = size === "sm" ? "size-8" : "size-10";
  const radius = shape === "circle" ? "rounded-full" : "rounded-xl";
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label={label}
      title={label}
      className={`grid ${sizing} shrink-0 place-items-center bg-control text-control-ink shadow-sm transition hover:brightness-105 active:scale-95 ${radius} ${
        active ? "ring-2 ring-accent/50" : ""
      } ${className}`}
    >
      {children}
    </button>
  );
}

function ToggleRow({
  label,
  checked,
  onChange
}: {
  label: string;
  checked: boolean;
  onChange: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onChange}
      className="flex w-full items-center gap-2.5 rounded-xl px-2.5 py-2 text-left text-[12.5px] font-medium text-ink transition hover:bg-panel-2"
    >
      <span
        className={`grid size-5 shrink-0 place-items-center rounded-[6px] border transition ${
          checked ? "border-accent bg-accent text-accent-ink" : "border-line-strong bg-transparent text-transparent"
        }`}
      >
        <Icon name="check" size={18} />
      </span>
      <span className="flex-1">{label}</span>
    </button>
  );
}

interface ControlsProps {
  theme: Theme;
  onToggleTheme: () => void;
  onZoomIn: () => void;
  onZoomOut: () => void;
  onReset: () => void;
  locating?: boolean;
  hasUserLocation?: boolean;
  layers: LayerToggles;
  onToggleLayer: (key: keyof LayerToggles) => void;
  lang: Lang;
  onToggleLang: (lang: Lang) => void;
  ui: UILabels;
}

export default function Controls({
  theme,
  onToggleTheme,
  onZoomIn,
  onZoomOut,
  onReset,
  locating = false,
  hasUserLocation = false,
  layers,
  onToggleLayer,
  lang,
  onToggleLang,
  ui
}: ControlsProps) {
  const [layersOpen, setLayersOpen] = useState(false);
  const [langOpen, setLangOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handlePointerDown(event: PointerEvent) {
      if (rootRef.current && !rootRef.current.contains(event.target as Node)) {
        setLayersOpen(false);
        setLangOpen(false);
      }
    }
    document.addEventListener("pointerdown", handlePointerDown);
    return () => document.removeEventListener("pointerdown", handlePointerDown);
  }, []);

  return (
    <div
      ref={rootRef}
      className="absolute right-3 top-3 z-40 flex w-11 flex-col items-center gap-2 sm:right-5 sm:top-5 sm:gap-2.5"
    >
      <ControlButton label={ui.theme} onClick={onToggleTheme}>
        <Icon name={theme === "dark" ? "sun" : "moon"} size={20} />
      </ControlButton>

      <div className="flex flex-col gap-1 rounded-full bg-timeline p-1 shadow-[0_4px_14px_rgba(0,0,0,0.12)]">
        <ControlButton label={ui.zoomIn} onClick={onZoomIn} size="sm" shape="circle">
          <Icon name="plus" size={18} />
        </ControlButton>
        <ControlButton label={ui.zoomOut} onClick={onZoomOut} size="sm" shape="circle">
          <Icon name="minus" size={18} />
        </ControlButton>
      </div>

      <div className="relative">
        <ControlButton
          label={ui.layers}
          active={layersOpen}
          onClick={() => {
            setLayersOpen((value) => !value);
            setLangOpen(false);
          }}
        >
          <Icon name="layers" size={20} />
        </ControlButton>
        {layersOpen ? (
          <div className="pop-in absolute right-0 top-[calc(100%+8px)] w-[184px] rounded-2xl border border-line/60 bg-search p-1.5 panel-shadow">
            <p className="px-2.5 pb-1 pt-1 text-[9.5px] font-semibold uppercase tracking-[0.16em] text-muted">
              {ui.layers}
            </p>
            <ToggleRow label={ui.labels} checked={layers.labels} onChange={() => onToggleLayer("labels")} />
            <ToggleRow label={ui.borders} checked={layers.borders} onChange={() => onToggleLayer("borders")} />
            <ToggleRow label={ui.graticule} checked={layers.graticule} onChange={() => onToggleLayer("graticule")} />
          </div>
        ) : null}
      </div>

      <ControlButton
        label={ui.currentLocation}
        onClick={onReset}
        active={hasUserLocation || locating}
      >
        <Icon
          name="locate"
          size={20}
          className={locating ? "animate-spin text-accent" : hasUserLocation ? "text-accent" : ""}
        />
      </ControlButton>

      <div className="relative self-end">
        {(() => {
          const currentLang = SUPPORTED_LANGUAGES.find((item) => item.code === lang) || SUPPORTED_LANGUAGES[0];
          return (
            <button
              type="button"
              onClick={() => {
                setLangOpen((value) => !value);
                setLayersOpen(false);
              }}
              aria-label={ui.language}
              aria-expanded={langOpen}
              title={ui.language}
              className={`flex h-9 items-center gap-1.5 rounded-full bg-control pl-2.5 pr-2 text-[11.5px] font-semibold text-control-ink shadow-sm transition hover:brightness-105 active:scale-95 sm:pl-3 sm:pr-2.5 ${
                langOpen ? "ring-2 ring-accent/55" : ""
              }`}
            >
              <Icon name="globe" size={16} className="text-accent" />
              <span className="tracking-wide sm:hidden">{currentLang.badge}</span>
              <span className="hidden whitespace-nowrap sm:inline">{currentLang.label}</span>
              <Icon
                name="chevron"
                size={16}
                className={`text-control-ink/80 transition duration-200 ${langOpen ? "rotate-180" : ""}`}
              />
            </button>
          );
        })()}

        {langOpen ? (
          <div className="pop-in absolute bottom-[calc(100%+8px)] right-0 w-[160px] rounded-2xl border border-line/60 bg-search p-1.5 panel-shadow sm:bottom-auto sm:top-[calc(100%+8px)]">
            <p className="px-2.5 pb-1 pt-1 text-[9.5px] font-semibold uppercase tracking-[0.16em] text-muted">
              {ui.language}
            </p>
            {SUPPORTED_LANGUAGES.map(({ code, label, badge }) => {
              const active = lang === code;
              return (
                <button
                  key={code}
                  type="button"
                  onClick={() => {
                    onToggleLang(code);
                    setLangOpen(false);
                  }}
                  className={`flex w-full items-center justify-between rounded-xl px-2.5 py-1.5 text-left text-[12px] font-medium transition ${
                    active
                      ? "bg-control font-semibold text-control-ink"
                      : "text-ink hover:bg-panel-2"
                  }`}
                >
                  <span className="flex items-center gap-2">
                    <span
                      className={`inline-flex h-4.5 w-5.5 items-center justify-center rounded text-[9.5px] font-bold tracking-wider ${
                        active
                          ? "bg-accent text-accent-ink"
                          : "bg-panel-2 text-muted"
                      }`}
                    >
                      {badge}
                    </span>
                    <span>{label}</span>
                  </span>
                  {active ? <Icon name="check" size={16} className="text-accent" /> : null}
                </button>
              );
            })}
          </div>
        ) : null}
      </div>
    </div>
  );
}
