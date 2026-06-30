"use client";

import { useMemo, useRef } from "react";
import { TOKENS } from "../styles/atlassianTokens";
import { BoardLane } from "./BoardLane";
import { FlowOverlay } from "./FlowOverlay";
import type { Actor, Lane, Ticket, ViewMode } from "../types";
import type { FlowMode, GroupMode } from "./TopBarV3";

interface Props {
  lanes: Lane[];
  tickets: Ticket[];
  viewMode: ViewMode;
  focusedTicketId: string | null;
  relatedIds: Set<string>;
  onTicketClick: (t: Ticket) => void;
  /**
   * v3 swimlane axis toggle.
   *   "phase" — Lane.parent / Lane.label (Product / Meta / Control)
   *   "agent" — synthesized from ticket.actor (Director / Claude Code / GPT / System)
   */
  groupMode: GroupMode;
  /**
   * v3 PR-5: Flow 점선 overlay 토글.
   *   "on"  — 강조 카드 ↔ 인접 카드 bezier (Phase: same-lane only / Agent: cross-lane OK)
   *   "off" — overlay 숨김
   */
  flowMode: FlowMode;
}

// Agent swimlane order: Director(사람) → Claude Code → GPT → System.
const AGENT_ORDER: Actor[] = ["Director", "Claude Code", "GPT", "System"];

// Director-facing outcome lines per agent — frames "what this swimlane is for".
const AGENT_OUTCOME: Record<Actor, string> = {
  "Director":    "사람 의사 결정 · HCP 승인 · 본질 정의",
  "Claude Code": "구현 · 코드 박제 · 검증 실행",
  "GPT":         "오케스트레이션 · 기획 받아쓰기",
  "System":      "자동 신호 · 컨트롤 플레인",
};

interface SwimlaneRow {
  lane: Lane;
  tickets: Ticket[];
}

function buildAgentLanes(tickets: Ticket[]): SwimlaneRow[] {
  const buckets = new Map<Actor, Ticket[]>();
  for (const t of tickets) {
    const actor: Actor = t.actor ?? "System";
    const arr = buckets.get(actor) ?? [];
    arr.push(t);
    buckets.set(actor, arr);
  }
  const rows: SwimlaneRow[] = [];
  for (const actor of AGENT_ORDER) {
    const arr = buckets.get(actor);
    if (!arr || arr.length === 0) continue;
    rows.push({
      lane: {
        id: `agent-${actor}`,
        label: actor,
        parent: "Agent",
        outcome: AGENT_OUTCOME[actor],
      },
      tickets: arr,
    });
  }
  return rows;
}

function buildPhaseLanes(lanes: Lane[], tickets: Ticket[]): SwimlaneRow[] {
  const rows: SwimlaneRow[] = [];
  for (const lane of lanes) {
    const laneTickets = tickets.filter((t) => t.lane === lane.id);
    if (laneTickets.length === 0) continue;
    rows.push({ lane, tickets: laneTickets });
  }
  return rows;
}

export function ProjectControlBoard({
  lanes,
  tickets,
  viewMode,
  focusedTicketId,
  relatedIds,
  onTicketClick,
  groupMode,
  flowMode,
}: Props) {
  const rows = useMemo<SwimlaneRow[]>(
    () =>
      groupMode === "agent"
        ? buildAgentLanes(tickets)
        : buildPhaseLanes(lanes, tickets),
    [groupMode, lanes, tickets],
  );

  // Flow 연결 id — Phase view 면 same-lane 만 통과시켜 cross-swimlane 그림 방지.
  // relatedIds 는 focused id 자기 자신을 포함 (dim 처리용) — flow 에서는 제외.
  const flowIds = useMemo<Set<string>>(() => {
    if (flowMode !== "on" || !focusedTicketId || relatedIds.size === 0) {
      return new Set<string>();
    }
    const focused = tickets.find((t) => t.id === focusedTicketId);
    if (!focused) return new Set<string>();
    const filtered = new Set<string>();
    relatedIds.forEach((rid) => {
      if (rid === focusedTicketId) return; // self-curve 방지
      if (groupMode === "agent") {
        filtered.add(rid);
        return;
      }
      const r = tickets.find((t) => t.id === rid);
      if (r && r.lane === focused.lane) filtered.add(rid);
    });
    return filtered;
  }, [flowMode, groupMode, focusedTicketId, relatedIds, tickets]);

  const flowContainerRef = useRef<HTMLDivElement>(null);

  return (
    <main
      className="flex h-full flex-col overflow-y-auto"
      style={{ background: TOKENS.bg }}
      aria-label="Project Control Board"
    >
      <div className="overflow-x-auto p-3" style={{ minWidth: 0 }}>
        <div ref={flowContainerRef} style={{ minWidth: 1200, position: "relative" }}>
          {rows.map(({ lane, tickets: laneTickets }) => (
            <BoardLane
              key={lane.id}
              lane={lane}
              tickets={laneTickets}
              viewMode={viewMode}
              focusedTicketId={focusedTicketId}
              relatedIds={relatedIds}
              onTicketClick={onTicketClick}
            />
          ))}
          {tickets.length === 0 && (
            <div
              className="rounded-md p-6 text-center text-sm"
              style={{
                color: TOKENS.textMuted,
                background: TOKENS.bgWhite,
                border: `1px dashed ${TOKENS.border}`,
              }}
            >
              No cards in this scope.
            </div>
          )}
          <FlowOverlay
            containerRef={flowContainerRef}
            focusedTicketId={focusedTicketId}
            flowIds={flowIds}
            enabled={flowMode === "on"}
          />
        </div>
      </div>
    </main>
  );
}
