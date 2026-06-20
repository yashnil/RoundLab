"use client";

import { TabsRoot, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import ArgumentHealthMatrix from "@/components/ArgumentHealthMatrix";
import JudgeLensComparison from "@/components/JudgeLensComparison";
import ImprovementLanes from "@/components/marketing/ImprovementLanes";

/**
 * Tabbed showcase of three core RoundLab product surfaces.
 *
 * Each illustration is wrapped in aria-hidden — the heading and description text
 * in each panel are the accessible names. The illustrations are decorative graphics.
 */
export default function ProductProofTabs() {
  return (
    <TabsRoot defaultValue="flow" className="flex flex-col gap-4">
      <div className="flex justify-center">
        <TabsList>
          <TabsTrigger value="flow">Argument flow</TabsTrigger>
          <TabsTrigger value="ballot">Judge ballot</TabsTrigger>
          <TabsTrigger value="improvement">Improvement</TabsTrigger>
        </TabsList>
      </div>

      <TabsContent value="flow">
        <div className="rounded-2xl border border-hairline bg-surface-1 p-5">
          <div className="mb-4">
            <p className="text-heading text-ink">Flow diagnostic board</p>
            <p className="mt-1 text-sm text-ink-subtle">
              CWEIM structure per contention — strong links, weak warrants, and missing evidence
              surfaced before a flow judge finds them.
            </p>
          </div>
          <div aria-hidden="true">
            <ArgumentHealthMatrix />
          </div>
        </div>
      </TabsContent>

      <TabsContent value="ballot">
        <div className="rounded-2xl border border-hairline bg-surface-1 p-5">
          <div className="mb-4">
            <p className="text-heading text-ink">One speech, four judges</p>
            <p className="mt-1 text-sm text-ink-subtle">
              The lens reorders what matters and rewrites the feedback — lay, flow, tech, or coach.
              Not a swapped badge.
            </p>
          </div>
          <div aria-hidden="true">
            <JudgeLensComparison />
          </div>
        </div>
      </TabsContent>

      <TabsContent value="improvement">
        <p className="sr-only">
          Side-by-side comparison showing argument improvement after drilling: added warrant, real
          weighing, and named impact.
        </p>
        <div aria-hidden="true">
          <ImprovementLanes />
        </div>
      </TabsContent>
    </TabsRoot>
  );
}
