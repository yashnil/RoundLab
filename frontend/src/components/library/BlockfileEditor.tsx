"use client";

import { useState, useEffect } from "react";
import {
  GripVertical, Plus, Trash2, Copy, ChevronDown, ChevronRight, FileText,
} from "lucide-react";
import { apiFetch } from "@/lib/api";
import type { Blockfile, BlockfileSection, BlockfileEntry, SectionType } from "@/types/library";

const SECTION_TYPE_LABELS: Record<SectionType, string> = {
  constructive: "Constructive",
  definitions: "Definitions / Framework",
  framework: "Framework",
  contention: "Contention",
  uniqueness: "Uniqueness",
  link: "Link",
  internal_link: "Internal Link",
  impact: "Impact",
  responses: "Responses",
  frontlines: "Frontlines",
  turns: "Turns",
  defense: "Defense",
  weighing: "Weighing",
  extensions: "Extensions",
  crossfire: "Crossfire Questions",
  miscellaneous: "Miscellaneous",
};

interface BlockfileEditorProps {
  blockfile: Blockfile;
  userId: string;
}

interface SectionWithEntries extends BlockfileSection {
  entries: BlockfileEntry[];
  collapsed: boolean;
}

export function BlockfileEditor({ blockfile, userId }: BlockfileEditorProps) {
  const [sections, setSections] = useState<SectionWithEntries[]>([]);
  const [loading, setLoading] = useState(true);
  const [addingSectionTitle, setAddingSectionTitle] = useState("");
  const [addingSectionType, setAddingSectionType] = useState<SectionType>("miscellaneous");
  const [showAddSection, setShowAddSection] = useState(false);

  async function load() {
    setLoading(true);
    try {
      const sects = await apiFetch(
        `/library/blockfiles/${blockfile.id}/sections?user_id=${userId}`,
      ) as BlockfileSection[];
      const withEntries = await Promise.all(
        sects.map(async (s) => {
          const entries = await apiFetch(`/library/sections/${s.id}/entries`) as BlockfileEntry[];
          return { ...s, entries, collapsed: false };
        }),
      );
      setSections(withEntries.sort((a, b) => a.position - b.position));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, [blockfile.id, userId]);

  async function addSection() {
    if (!addingSectionTitle.trim()) return;
    try {
      const newSect = await apiFetch(`/library/blockfiles/${blockfile.id}/sections`, {
        method: "POST",
        body: JSON.stringify({
          blockfile_id: blockfile.id,
          user_id: userId,
          title: addingSectionTitle.trim(),
          section_type: addingSectionType,
          position: sections.length,
        }),
      }) as BlockfileSection;
      setSections((prev) => [...prev, { ...newSect, entries: [], collapsed: false }]);
      setAddingSectionTitle("");
      setShowAddSection(false);
    } catch {}
  }

  async function deleteSection(sectionId: string) {
    if (!confirm("Delete section and all its entries?")) return;
    try {
      await apiFetch(`/library/sections/${sectionId}?user_id=${userId}`, { method: "DELETE" });
      setSections((prev) => prev.filter((s) => s.id !== sectionId));
    } catch {}
  }

  async function duplicateSection(sectionId: string) {
    try {
      const newSect = await apiFetch(`/library/sections/${sectionId}/duplicate`, {
        method: "POST",
        body: JSON.stringify({ user_id: userId, section_id: sectionId }),
      }) as BlockfileSection;
      await load();
    } catch {}
  }

  async function removeEntry(sectionId: string, entryId: string) {
    try {
      await apiFetch(`/library/entries/${entryId}?user_id=${userId}`, { method: "DELETE" });
      setSections((prev) =>
        prev.map((s) =>
          s.id === sectionId
            ? { ...s, entries: s.entries.filter((e) => e.id !== entryId) }
            : s,
        ),
      );
    } catch {}
  }

  function toggleSection(sectionId: string) {
    setSections((prev) =>
      prev.map((s) =>
        s.id === sectionId ? { ...s, collapsed: !s.collapsed } : s,
      ),
    );
  }

  if (loading) {
    return <div className="py-8 text-center text-[12px] text-ink-subtle">Loading blockfile…</div>;
  }

  return (
    <div className="space-y-3">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-[16px] font-semibold text-ink">{blockfile.title}</h2>
          {blockfile.side && (
            <span className="text-[11px] text-ink-subtle capitalize">{blockfile.side}</span>
          )}
        </div>
        <button
          onClick={() => setShowAddSection(!showAddSection)}
          className="flex items-center gap-1.5 text-[12px] px-3 py-1.5 rounded-lg border border-border text-ink hover:bg-surface-muted transition-colors"
        >
          <Plus size={13} />
          Add Section
        </button>
      </div>

      {/* Add section form */}
      {showAddSection && (
        <div className="rounded-lg border border-border bg-surface-muted p-3 space-y-2">
          <input
            value={addingSectionTitle}
            onChange={(e) => setAddingSectionTitle(e.target.value)}
            placeholder="Section title"
            className="w-full text-[13px] border border-border rounded-md px-2.5 py-1.5 bg-surface-1 text-ink"
          />
          <select
            value={addingSectionType}
            onChange={(e) => setAddingSectionType(e.target.value as SectionType)}
            className="w-full text-[13px] border border-border rounded-md px-2.5 py-1.5 bg-surface-1 text-ink"
          >
            {(Object.entries(SECTION_TYPE_LABELS) as [SectionType, string][]).map(([k, v]) => (
              <option key={k} value={k}>{v}</option>
            ))}
          </select>
          <div className="flex gap-2">
            <button
              onClick={addSection}
              className="flex-1 text-[12px] py-1.5 rounded-md bg-ink text-canvas hover:bg-ink/80"
            >
              Add
            </button>
            <button
              onClick={() => setShowAddSection(false)}
              className="text-[12px] px-3 py-1.5 rounded-md border border-border text-ink-subtle"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Sections */}
      {sections.length === 0 && (
        <div className="py-12 text-center text-[12px] text-ink-subtle">
          <FileText size={24} className="mx-auto mb-2 opacity-30" />
          <p>No sections yet. Add a section to start organizing cards.</p>
        </div>
      )}

      {sections.map((sect) => (
        <div key={sect.id} className="rounded-xl border border-border overflow-hidden">
          {/* Section header */}
          <div className="flex items-center gap-2 px-3 py-2.5 bg-surface-muted border-b border-hairline">
            <GripVertical size={14} className="text-ink-faint shrink-0 cursor-grab" />
            <button
              onClick={() => toggleSection(sect.id)}
              className="flex items-center gap-1.5 flex-1 min-w-0 text-left"
            >
              {sect.collapsed ? (
                <ChevronRight size={13} className="text-ink-subtle shrink-0" />
              ) : (
                <ChevronDown size={13} className="text-ink-subtle shrink-0" />
              )}
              <span className="text-[13px] font-semibold text-ink truncate">{sect.title}</span>
              <span className="text-[10px] text-ink-subtle">
                {SECTION_TYPE_LABELS[sect.section_type]}
              </span>
              <span className="text-[10px] text-ink-faint ml-auto shrink-0">
                {sect.entries.length} card{sect.entries.length !== 1 ? "s" : ""}
              </span>
            </button>
            <div className="flex items-center gap-1 shrink-0">
              <button
                onClick={() => duplicateSection(sect.id)}
                className="p-1 rounded text-ink-subtle hover:bg-surface-hover transition-colors"
                aria-label="Duplicate section"
                title="Duplicate"
              >
                <Copy size={13} />
              </button>
              <button
                onClick={() => deleteSection(sect.id)}
                className="p-1 rounded text-ink-subtle hover:text-danger hover:bg-danger/10 transition-colors"
                aria-label="Delete section"
                title="Delete section"
              >
                <Trash2 size={13} />
              </button>
            </div>
          </div>

          {/* Section entries */}
          {!sect.collapsed && (
            <div className="divide-y divide-hairline">
              {sect.entries.length === 0 && (
                <p className="py-4 text-center text-[11px] text-ink-subtle">
                  No cards in this section.
                </p>
              )}
              {sect.entries.map((entry) => (
                <div key={entry.id} className="flex items-start gap-2.5 px-3 py-2.5 hover:bg-surface-muted/50 transition-colors">
                  <GripVertical size={13} className="text-ink-faint mt-0.5 shrink-0 cursor-grab" />
                  <div className="flex-1 min-w-0">
                    {entry.entry_type === "analytical_note" ? (
                      <p className="text-[12px] text-ink-subtle italic">
                        {entry.notes || entry.custom_label || "Analytical note"}
                      </p>
                    ) : entry.entry_type === "header" ? (
                      <p className="text-[13px] font-semibold text-ink">
                        {entry.custom_label}
                      </p>
                    ) : (
                      <>
                        <p className="text-[12px] font-medium text-ink truncate">
                          {entry.custom_label || entry.card_id}
                        </p>
                        {entry.notes && (
                          <p className="text-[10px] text-ink-subtle">{entry.notes}</p>
                        )}
                      </>
                    )}
                  </div>
                  <button
                    onClick={() => removeEntry(sect.id, entry.id)}
                    className="p-1 rounded text-ink-faint hover:text-danger hover:bg-danger/10 transition-colors shrink-0"
                    aria-label="Remove from blockfile"
                    title="Remove from blockfile (does not delete the card)"
                  >
                    <Trash2 size={12} />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
