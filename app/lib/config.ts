// Centralized runtime config for data-source selection.
// ONLY this file reads Vite env vars. Other files must import from here.
export const USE_MOCK = (import.meta as any).env?.VITE_USE_MOCK === "true";

export const API_BASE_URL = (import.meta as any).env?.VITE_API_BASE_URL || "http://127.0.0.1:8000";

// DEV-only informational log to make data-source explicit on page load.
// This runs once when the module is imported by the app.
try {
	// eslint-disable-next-line no-console
	console.log("[DATA SOURCE]", USE_MOCK ? "MOCK" : "LIVE", API_BASE_URL);
} catch (e) {
	// swallow logging errors in constrained environments
}
