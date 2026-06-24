"use client";

import React, { useState, useCallback } from "react";
import {
  CitationRecord,
  CitationCompleteness,
  ConfidenceTier,
  MetadataSource,
} from "@/types";

// ── Format options ─────────────────────────────────────────────────────────

type CitationFormat = "debate" | "mla" | "apa" | "chicago" | "bibtex" | "ris" | "csl_json";

const FORMAT_LABELS: Record<CitationFormat, string> = {
  debate: "Debate",
  mla: "MLA",
  apa: "APA",
  chicago: "Chicago",
  bibtex: "BibTeX",
  ris: "RIS",
  csl_json: "CSL-JSON",
};

// ── Confidence display ─────────────────────────────────────────────────────

const CONFIDENCE_LABELS: Record<ConfidenceTier, string> = {
  verified: "Verified",
  high: "High",
  medium: "Medium",
  low: "Low",
  unknown: "Unknown",
};

const CONFIDENCE_COLORS: Record<ConfidenceTier, string> = {
  verified: "text-emerald-600",
  high: "text-sky-600",
  medium: "text-amber-600",
  low: "text-orange-500",
  unknown: "text-ink-subtle",
};

const SOURCE_LABELS: Record<MetadataSource, string> = {
  user_edit: "Your edit",
  crossref: "Crossref DOI",
  openalex: "OpenAlex",
  semantic_scholar: "Semantic Scholar",
  json_ld: "JSON-LD",
  citation_meta: "Citation meta tag",
  og: "OpenGraph",
  pdf_parser: "PDF parser",
  docx_parser: "DOCX parser",
  provider_metadata: "Search provider",
  visible_text: "Page text",
  url_inference: "URL",
  domain_inference: "Domain",
  none: "Not detected",
};

// ── Completeness badge ────────────────────────────────────────────────────

const COMPLETENESS_COLORS: Record<CitationCompleteness, string> = {
  complete: "bg-emerald-100 text-emerald-800",
  usable_with_warnings: "bg-amber-100 text-amber-800",
  incomplete: "bg-orange-100 text-orange-800",
  unverified: "bg-surface-muted text-ink-subtle",
};

const COMPLETENESS_LABELS: Record<CitationCompleteness, string> = {
  complete: "Complete",
  usable_with_warnings: "Usable",
  incomplete: "Incomplete",
  unverified: "Unverified",
};

// ── Person display ────────────────────────────────────────────────────────

function formatPerson(p: CitationRecord["authors"][0]): string {
  if (p.is_organization) return p.literal || p.family;
  if (p.family && p.given) return `${p.given} ${p.family}`;
  return p.literal || p.family || p.given || "";
}

// ── Rendered citation for the selected format ─────────────────────────────

function getRendered(record: CitationRecord, fmt: CitationFormat): string {
  switch (fmt) {
    case "debate": return record.rendered_debate || "";
    case "mla":    return record.rendered_mla || "";
    case "apa":    return record.rendered_apa || "";
    case "chicago": return record.rendered_chicago || "";
    case "bibtex": return record.rendered_bibtex || "";
    case "ris":    return record.rendered_ris || "";
    case "csl_json":
      try {
        return JSON.stringify(
          JSON.parse(record.rendered_ris || "{}"),
          null,
          2,
        );
      } catch {
        return "";
      }
    default:       return "";
  }
}

// ── Copy helper ───────────────────────────────────────────────────────────

async function copyToClipboard(text: string): Promise<boolean> {
  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(text);
      return true;
    }
    const el = document.createElement("textarea");
    el.value = text;
    el.style.position = "fixed";
    el.style.opacity = "0";
    document.body.appendChild(el);
    el.focus();
    el.select();
    const ok = document.execCommand("copy");
    document.body.removeChild(el);
    return ok;
  } catch {
    return false;
  }
}

// ── Props ─────────────────────────────────────────────────────────────────

export interface CitationDetailsPanelProps {
  record: CitationRecord;
  /** Called when user edits a field (field name, new value as string). */
  onFieldEdit?: (field: string, value: string) => void;
  /** Fallback MLA string for legacy cards that have no CitationRecord. */
  legacyMla?: string;
  defaultOpen?: boolean;
}

// ── Component ─────────────────────────────────────────────────────────────

export function CitationDetailsPanel({
  record,
  onFieldEdit,
  legacyMla,
  defaultOpen = false,
}: CitationDetailsPanelProps) {
  const [format, setFormat] = useState<CitationFormat>("debate");
  const [open, setOpen] = useState(defaultOpen);
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const [copied, setCopied] = useState(false);
  const [editField, setEditField] = useState<string | null>(null);
  const [editValue, setEditValue] = useState("");

  const rendered = getRendered(record, format) || legacyMla || "";

  const handleCopy = useCallback(async () => {
    if (!rendered) return;
    const ok = await copyToClipboard(rendered);
    if (ok) {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  }, [rendered]);

  const handleDownload = useCallback(
    (fmt: "bibtex" | "ris" | "csl_json") => {
      const content = getRendered(record, fmt);
      if (!content) return;
      const ext = fmt === "bibtex" ? "bib" : fmt === "ris" ? "ris" : "json";
      const mime =
        fmt === "csl_json" ? "application/json" : "text/plain";
      const blob = new Blob([content], { type: mime });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `citation.${ext}`;
      a.click();
      URL.revokeObjectURL(url);
    },
    [record],
  );

  const startEdit = (field: string, currentValue: string) => {
    setEditField(field);
    setEditValue(currentValue);
  };

  const commitEdit = () => {
    if (editField && onFieldEdit) {
      onFieldEdit(editField, editValue);
    }
    setEditField(null);
    setEditValue("");
  };

  const cancelEdit = () => {
    setEditField(null);
    setEditValue("");
  };

  if (!record) {
    // Legacy fallback: just show the MLA string
    if (legacyMla) {
      return (
        <div className="text-sm font-mono text-ink-subtle p-3 bg-surface-muted rounded">
          {legacyMla}
        </div>
      );
    }
    return null;
  }

  return (
    <div className="border border-surface-border rounded-md overflow-hidden text-sm">
      {/* Header row */}
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center justify-between px-3 py-2 bg-surface-muted hover:bg-surface-hover transition-colors text-left"
        aria-expanded={open}
      >
        <span className="flex items-center gap-2 font-medium text-ink-base">
          Citation
          <span
            className={`text-xs px-1.5 py-0.5 rounded font-normal ${
              COMPLETENESS_COLORS[record.completeness]
            }`}
          >
            {COMPLETENESS_LABELS[record.completeness]}
          </span>
          {record.conflicts.length > 0 && (
            <span className="text-xs px-1.5 py-0.5 rounded bg-amber-100 text-amber-800">
              {record.conflicts.length} conflict{record.conflicts.length > 1 ? "s" : ""}
            </span>
          )}
        </span>
        <span className="text-ink-subtle">{open ? "▲" : "▼"}</span>
      </button>

      {open && (
        <div className="p-3 space-y-3">
          {/* Format selector */}
          <div className="flex flex-wrap gap-1" role="tablist" aria-label="Citation format">
            {(Object.keys(FORMAT_LABELS) as CitationFormat[]).map((f) => (
              <button
                key={f}
                role="tab"
                aria-selected={format === f}
                onClick={() => setFormat(f)}
                className={`px-2 py-0.5 text-xs rounded border transition-colors ${
                  format === f
                    ? "bg-lav/10 border-lav/30 text-lav font-medium"
                    : "border-surface-border text-ink-subtle hover:text-ink-base"
                }`}
              >
                {FORMAT_LABELS[f]}
              </button>
            ))}
          </div>

          {/* Rendered citation */}
          <div className="relative">
            <div
              className={`font-mono text-xs p-2 rounded bg-surface-muted border border-surface-border whitespace-pre-wrap break-all leading-relaxed ${
                format === "debate" ? "font-sans text-sm font-medium" : ""
              }`}
            >
              {rendered || (
                <span className="text-ink-subtle italic">No citation available</span>
              )}
            </div>
            <div className="flex gap-2 mt-1.5 flex-wrap">
              <button
                onClick={handleCopy}
                className="text-xs text-ink-subtle hover:text-ink-base transition-colors"
              >
                {copied ? "Copied!" : "Copy"}
              </button>
              {format === "bibtex" && (
                <button
                  onClick={() => handleDownload("bibtex")}
                  className="text-xs text-ink-subtle hover:text-ink-base transition-colors"
                >
                  Download .bib
                </button>
              )}
              {format === "ris" && (
                <button
                  onClick={() => handleDownload("ris")}
                  className="text-xs text-ink-subtle hover:text-ink-base transition-colors"
                >
                  Download .ris
                </button>
              )}
              {format === "csl_json" && (
                <button
                  onClick={() => handleDownload("csl_json")}
                  className="text-xs text-ink-subtle hover:text-ink-base transition-colors"
                >
                  Download .json
                </button>
              )}
            </div>
          </div>

          {/* Conflicts */}
          {record.conflicts.length > 0 && (
            <div className="space-y-1">
              <p className="text-xs font-medium text-amber-700">Metadata conflicts detected:</p>
              {record.conflicts.map((c, i) => (
                <div key={i} className="text-xs text-amber-700 bg-amber-50 rounded px-2 py-1">
                  {c.message}
                </div>
              ))}
            </div>
          )}

          {/* Warnings */}
          {record.warnings.length > 0 && (
            <div className="space-y-1">
              {record.warnings.map((w, i) => (
                <p key={i} className="text-xs text-orange-600">{w}</p>
              ))}
            </div>
          )}

          {/* Core fields */}
          <FieldRow
            label="Authors"
            value={record.authors.map(formatPerson).join("; ") || ""}
            prov={record.authors_prov}
            field="authors"
            editField={editField}
            editValue={editValue}
            onEdit={onFieldEdit ? startEdit : undefined}
            onCommit={commitEdit}
            onCancel={cancelEdit}
            onEditValueChange={setEditValue}
          />
          <FieldRow
            label="Title"
            value={record.title || record.legislation_title || record.case_name || ""}
            prov={record.title_prov}
            field="title"
            editField={editField}
            editValue={editValue}
            onEdit={onFieldEdit ? startEdit : undefined}
            onCommit={commitEdit}
            onCancel={cancelEdit}
            onEditValueChange={setEditValue}
          />
          <FieldRow
            label="Publication"
            value={record.container_title || record.publisher || ""}
            prov={record.container_title || record.container_title_prov.source !== "none"
              ? record.container_title_prov
              : record.publisher_prov}
            field="container_title"
            editField={editField}
            editValue={editValue}
            onEdit={onFieldEdit ? startEdit : undefined}
            onCommit={commitEdit}
            onCancel={cancelEdit}
            onEditValueChange={setEditValue}
          />
          <FieldRow
            label="Year"
            value={record.issued?.year ? String(record.issued.year) : ""}
            prov={record.issued_prov}
            field="issued_year"
            editField={editField}
            editValue={editValue}
            onEdit={onFieldEdit ? startEdit : undefined}
            onCommit={commitEdit}
            onCancel={cancelEdit}
            onEditValueChange={setEditValue}
          />

          {/* DOI / URL */}
          {record.doi && (
            <div className="flex items-center gap-2 text-xs">
              <span className="text-ink-subtle w-20 shrink-0">DOI</span>
              <a
                href={`https://doi.org/${record.doi}`}
                target="_blank"
                rel="noopener noreferrer"
                className="text-sky-600 hover:underline truncate"
              >
                {record.doi}
              </a>
              <ProvenanceBadge prov={record.doi_prov} />
            </div>
          )}
          {record.url && !record.doi && (
            <div className="flex items-center gap-2 text-xs">
              <span className="text-ink-subtle w-20 shrink-0">URL</span>
              <a
                href={record.url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-sky-600 hover:underline truncate"
              >
                {record.url}
              </a>
            </div>
          )}

          {/* Advanced metadata (collapsed) */}
          <button
            type="button"
            onClick={() => setAdvancedOpen((v) => !v)}
            className="text-xs text-ink-subtle hover:text-ink-base"
          >
            {advancedOpen ? "Hide" : "Show"} advanced metadata
          </button>

          {advancedOpen && (
            <div className="space-y-1.5 pt-1 border-t border-surface-border">
              <p className="text-xs font-medium text-ink-subtle">Source type</p>
              <p className="text-xs text-ink-base">{record.source_type}</p>

              {record.volume && (
                <SimpleRow label="Volume" value={record.volume} />
              )}
              {record.issue && (
                <SimpleRow label="Issue" value={record.issue} />
              )}
              {record.page && (
                <SimpleRow label="Pages" value={record.page} />
              )}
              {record.institution && (
                <SimpleRow label="Institution" value={record.institution} />
              )}
              {record.report_number && (
                <SimpleRow label="Report #" value={record.report_number} />
              )}
              {record.court && (
                <SimpleRow label="Court" value={record.court} />
              )}
              {record.case_name && !record.title && (
                <SimpleRow label="Case" value={record.case_name} />
              )}
              {record.docket_number && (
                <SimpleRow label="Docket" value={record.docket_number} />
              )}
              {record.language && (
                <SimpleRow label="Language" value={record.language} />
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ── Sub-components ────────────────────────────────────────────────────────

function ProvenanceBadge({
  prov,
}: {
  prov: import("@/types").FieldProvenance | undefined;
}) {
  if (!prov || prov.source === "none") return null;
  const conf = prov.confidence as ConfidenceTier;
  return (
    <span
      title={`Source: ${SOURCE_LABELS[prov.source as MetadataSource] ?? prov.source} — ${CONFIDENCE_LABELS[conf] ?? conf} confidence${prov.manually_edited ? " (edited)" : ""}`}
      className={`text-[10px] ${CONFIDENCE_COLORS[conf] ?? "text-ink-subtle"} cursor-help`}
    >
      {prov.manually_edited ? "✏ edited" : CONFIDENCE_LABELS[conf] ?? conf}
    </span>
  );
}

interface FieldRowProps {
  label: string;
  value: string;
  prov: import("@/types").FieldProvenance | undefined;
  field: string;
  editField: string | null;
  editValue: string;
  onEdit?: (field: string, value: string) => void;
  onCommit: () => void;
  onCancel: () => void;
  onEditValueChange: (v: string) => void;
}

function FieldRow({
  label,
  value,
  prov,
  field,
  editField,
  editValue,
  onEdit,
  onCommit,
  onCancel,
  onEditValueChange,
}: FieldRowProps) {
  const isEditing = editField === field;

  return (
    <div className="flex items-start gap-2 text-xs">
      <span className="text-ink-subtle w-20 shrink-0 pt-0.5">{label}</span>
      {isEditing ? (
        <div className="flex-1 flex gap-1">
          <input
            type="text"
            value={editValue}
            onChange={(e) => onEditValueChange(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") onCommit();
              if (e.key === "Escape") onCancel();
            }}
            className="flex-1 border border-lav/40 rounded px-1.5 py-0.5 text-xs focus:outline-none focus:ring-1 focus:ring-lav/50"
            autoFocus
          />
          <button
            onClick={onCommit}
            className="text-xs text-emerald-600 hover:text-emerald-700 font-medium px-1"
          >
            Save
          </button>
          <button
            onClick={onCancel}
            className="text-xs text-ink-subtle hover:text-ink-base px-1"
          >
            Cancel
          </button>
        </div>
      ) : (
        <div className="flex-1 flex items-center gap-1.5">
          <span className={value ? "text-ink-base" : "text-ink-subtle italic"}>
            {value || "Not detected"}
          </span>
          {prov && <ProvenanceBadge prov={prov} />}
          {onEdit && (
            <button
              onClick={() => onEdit(field, value)}
              className="ml-auto text-ink-subtle hover:text-ink-base text-[10px] opacity-0 group-hover:opacity-100 transition-opacity"
              title="Edit this field"
            >
              edit
            </button>
          )}
        </div>
      )}
    </div>
  );
}

function SimpleRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center gap-2 text-xs">
      <span className="text-ink-subtle w-20 shrink-0">{label}</span>
      <span className="text-ink-base">{value}</span>
    </div>
  );
}
