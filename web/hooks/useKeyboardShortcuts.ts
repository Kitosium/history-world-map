"use client";

import { useEffect } from "react";

interface KeyboardShortcutHandlers {
  onTogglePlay: () => void;
  onStepPrev: () => void;
  onStepNext: () => void;
  onZoomIn: () => void;
  onZoomOut: () => void;
  onClearSelection: () => void;
}

export function useKeyboardShortcuts({
  onTogglePlay,
  onStepPrev,
  onStepNext,
  onZoomIn,
  onZoomOut,
  onClearSelection
}: KeyboardShortcutHandlers) {
  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      const target = event.target as HTMLElement | null;
      const tag = target?.tagName;
      const isEditing =
        tag === "INPUT" ||
        tag === "TEXTAREA" ||
        tag === "SELECT" ||
        Boolean(target?.isContentEditable);

      if (isEditing) return;

      if (event.key === " " || event.code === "Space") {
        event.preventDefault();
        onTogglePlay();
      } else if (event.key === "ArrowLeft") {
        event.preventDefault();
        onStepPrev();
      } else if (event.key === "ArrowRight") {
        event.preventDefault();
        onStepNext();
      } else if (event.key === "+" || event.key === "=") {
        event.preventDefault();
        onZoomIn();
      } else if (event.key === "-" || event.key === "_") {
        event.preventDefault();
        onZoomOut();
      } else if (event.key === "/") {
        const searchInput = document.querySelector<HTMLInputElement>(
          'input[data-atlas-search="true"]'
        );
        if (searchInput) {
          event.preventDefault();
          searchInput.focus();
          searchInput.select();
        }
      } else if (event.key === "Escape") {
        onClearSelection();
      }
    }

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onClearSelection, onStepNext, onStepPrev, onTogglePlay, onZoomIn, onZoomOut]);
}
