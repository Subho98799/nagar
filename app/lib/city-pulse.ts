/**
 * City Pulse API (read-only).
 *
 * Governance-first rules:
 * - No auth required
 * - No mutations
 * - Calm, summary-driven outputs only
 */

import { API_BASE_URL, USE_MOCK } from "~/lib/config";
import { mockIssues } from "~/data/mock-issues";

export type CityPulseResponse = {
  city: string;
  report_count: number;
  active_issues: Record<string, number>;
  confidence_breakdown: Record<string, number>;
  affected_localities: string[];
  summary: string;
};

export async function listPulseCities(): Promise<{ cities: string[]; count: number }> {
  if (USE_MOCK) {
    return { cities: ["Demo City"], count: 1 };
  }
  try {
    const res = await fetch(`${API_BASE_URL}/city-pulse/cities`);
    if (!res.ok) {
      throw new Error(`City list error ${res.status}`);
    }
    return res.json();
  } catch (err) {
    // Governance: never crash the UI on network/backend issues.
    // eslint-disable-next-line no-console
    console.error("listPulseCities error:", err);
    return { cities: [], count: 0 };
  }
}

export async function fetchCityPulse(city: string): Promise<CityPulseResponse> {
  if (USE_MOCK) {
    // Derive a calm pulse from the existing mock issues (read-only).
    const active = mockIssues.filter((i) => i.status === "Active");
    const active_issues: Record<string, number> = {};
    const confidence_breakdown: Record<string, number> = { LOW: 0, MEDIUM: 0, HIGH: 0 };
    const localities = new Set<string>();

    for (const i of active) {
      active_issues[i.type] = (active_issues[i.type] || 0) + 1;
      if (i.confidence === "High") confidence_breakdown.HIGH += 1;
      else if (i.confidence === "Medium") confidence_breakdown.MEDIUM += 1;
      else confidence_breakdown.LOW += 1;
      if (i.location) localities.add(i.location);
    }

    return {
      city,
      report_count: active.length,
      active_issues,
      confidence_breakdown,
      affected_localities: Array.from(localities).slice(0, 10),
      summary:
        active.length === 0
          ? `No active reports in ${city} at this time.`
          : `${active.length} active report(s) in ${city}. Situation is being monitored.`,
    };
  }

  const url = `${API_BASE_URL}/city-pulse?city=${encodeURIComponent(city)}`;
  try {
    const res = await fetch(url);
    if (!res.ok) {
      throw new Error(`City pulse error ${res.status}`);
    }
    return res.json();
  } catch (err) {
    // eslint-disable-next-line no-console
    console.error("fetchCityPulse error:", err);
    // Safe fallback so City Overview can still render a calm message.
    return {
      city,
      report_count: 0,
      active_issues: {},
      confidence_breakdown: {},
      affected_localities: [],
      summary: "No data available for this city at the moment.",
    };
  }
}

