"use client";

import { useId, useState, type ReactNode } from "react";

type CollapsibleSectionProps = {
  /** Header text displayed in the clickable toggle bar */
  title: string;
  /** Content to show/hide */
  children: ReactNode;
  /** Whether the section starts expanded (default: false) */
  defaultOpen?: boolean;
  /** Additional CSS classes for the header text */
  headerClassName?: string;
};

/**
 * A collapsible section with a clickable header and chevron indicator.
 *
 * Uses CSS `grid-template-rows` transition for smooth open/close animation
 * (the max-height approach requires a known height; grid rows transition
 * from 0fr to 1fr without that limitation).
 */
export default function CollapsibleSection({
  title,
  children,
  defaultOpen = false,
  headerClassName,
}: CollapsibleSectionProps) {
  const [isOpen, setIsOpen] = useState(defaultOpen);
  const contentId = useId();

  return (
    <section>
      <button
        type="button"
        onClick={() => setIsOpen((prev) => !prev)}
        className="mb-1 flex w-full items-center gap-1.5 text-left focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ink-black)] focus-visible:ring-offset-1 rounded"
        aria-expanded={isOpen}
        aria-controls={contentId}
      >
        {/* Chevron rotates 90deg when open */}
        <svg
          className="h-3 w-3 shrink-0 transition-transform duration-200"
          style={{ transform: isOpen ? "rotate(90deg)" : "rotate(0deg)" }}
          viewBox="0 0 12 12"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
        >
          <path d="M4 2 L8 6 L4 10" />
        </svg>
        <span
          role="heading"
          aria-level={3}
          className={
            headerClassName ??
            "text-xs font-semibold uppercase tracking-wide text-[#6B6560]"
          }
        >
          {title}
        </span>
      </button>

      {/*
        Grid-row transition: rows go from 0fr (collapsed) to 1fr (expanded).
        The inner div prevents content from being visible during collapse
        via overflow-hidden on the wrapper.
      */}
      <div
        id={contentId}
        className="grid transition-[grid-template-rows] duration-200 ease-in-out"
        style={{ gridTemplateRows: isOpen ? "1fr" : "0fr" }}
      >
        <div className="overflow-hidden">
          <div className="pt-1">{children}</div>
        </div>
      </div>
    </section>
  );
}
