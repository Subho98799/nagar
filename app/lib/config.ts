// Centralized runtime config for data-source selection.
// ONLY this file reads Vite env vars. Other files must import from here.
export const USE_MOCK = (import.meta as any).env?.VITE_USE_MOCK === "true";

export const API_BASE_URL = (import.meta as any).env?.VITE_API_BASE_URL || "http://127.0.0.1:8000";

/**
 * Governance-first feature flags.
 *
 * These are intentionally conservative defaults to avoid product drift during judging.
 * - Timeline feed: optional surface (can be enabled for demos)
 * - Analytics/charts: admin-only surface
 * - Votes/comments: non-authoritative signals (should never affect confidence/priority/escalation)
 */
export const ENABLE_TIMELINE = (import.meta as any).env?.VITE_ENABLE_TIMELINE === "true";
export const ENABLE_ADMIN_ANALYTICS = (import.meta as any).env?.VITE_ENABLE_ADMIN_ANALYTICS === "true";
export const ENABLE_SIGNAL_INPUTS = (import.meta as any).env?.VITE_ENABLE_SIGNAL_INPUTS === "true";

// Comma-separated allowlist of admin phone numbers (normalized digits, e.g. "916200015545,9174...")
export const ADMIN_PHONE_ALLOWLIST = ((import.meta as any).env?.VITE_ADMIN_PHONE_ALLOWLIST || "")
	.split(",")
	.map((s: string) => s.trim())
	.filter(Boolean);

// DEV-only informational log to make data-source explicit on page load.
// This runs once when the module is imported by the app.
try {
	// eslint-disable-next-line no-console
	console.log("[DATA SOURCE]", USE_MOCK ? "MOCK" : "LIVE", API_BASE_URL);
} catch (e) {
	// swallow logging errors in constrained environments
}
