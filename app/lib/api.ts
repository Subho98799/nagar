// Lightweight API client for frontend - fetches issues from backend
// Uses absolute backend URL from `API_BASE_URL` to avoid React Router handling API paths.
import { API_BASE_URL, USE_MOCK } from "~/lib/config";
import { mockIssues } from "~/data/mock-issues";

// Helper: convert frontend mock `Issue` shape to server `ServerIssue` shape
function mockToServerIssues(): ServerIssue[] {
  return mockIssues.map((m) => ({
    id: m.id,
    title: m.title,
    description: m.description,
    issue_type: m.type === "Traffic" ? "Traffic & Roads" : m.type === "Power" ? "Electricity" : m.type,
    severity: m.severity,
    // server uses uppercase confidence strings
    confidence: (m.confidence || "Low").toUpperCase() as ServerIssue["confidence"],
    status: m.status === "Active" ? "CONFIRMED" : m.status === "Resolved" ? "RESOLVED" : "UNDER_OBSERVATION",
    latitude: undefined,
    longitude: undefined,
    locality: undefined,
    city: undefined,
    report_count: m.reportCount || 1,
    created_at: m.timestamp,
    updated_at: m.timestamp,
  }));
}

export type ServerIssue = {
  id: string;
  title: string;
  description: string;
  issue_type: string;
  severity: "Low" | "Medium" | "High";
  confidence: "LOW" | "MEDIUM" | "HIGH";
  status: string;
  latitude?: number;
  longitude?: number;
  locality?: string;
  city?: string;
  report_count: number;
  created_at: string;
  updated_at: string;
  operatorNotes?: string | null;
  // Phase-4: Optional reverse-geocoded address fields (read-only display)
  resolved_address?: string | null;
  resolved_locality?: string | null;
  resolved_city?: string | null;
};

async function fetchJSON(url: string) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 5000);
  try {
    const res = await fetch(url, { signal: controller.signal });
    if (!res.ok) throw new Error(`API error ${res.status}`);
    return res.json();
  } finally {
    clearTimeout(timeout);
  }
}

export async function fetchIssues(city = "Demo City") {
  if (USE_MOCK) {
    // Return mock data converted to server shape so TypeScript and consumers see consistent fields.
    return Promise.resolve(mockToServerIssues());
  }

  const path = `/map/issues?city=${encodeURIComponent(city)}`;
  const url = `${API_BASE_URL}${path}`;
  try {
    return (await fetchJSON(url)) as ServerIssue[];
  } catch (err) {
    // Log and return empty array per requirements (do not fallback to mock)
    // eslint-disable-next-line no-console
    console.error("fetchIssues error:", err);
    return [];
  }
}

export async function fetchIssueById(id: string, city = "Demo City") {
  if (USE_MOCK) {
    const found = mockToServerIssues().find((i) => i.id === id);
    return Promise.resolve(found);
  }

  const issues = await fetchIssues(city);
  return issues.find((i) => i.id === id) as ServerIssue | undefined;
}
