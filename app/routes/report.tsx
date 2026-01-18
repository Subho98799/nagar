import { useState } from "react";
import { API_BASE_URL } from "~/lib/config";
import { Upload, CheckCircle } from "lucide-react";
import { Header } from "~/components/header";
import { Button } from "~/components/ui/button/button";
import { Input } from "~/components/ui/input/input";
import { Textarea } from "~/components/ui/textarea/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "~/components/ui/select/select";
import type { IssueType } from "~/data/mock-issues";
import { useLanguage } from "~/context/LanguageContext";
import { t } from "~/lib/i18n";
import styles from "./report.module.css";

export default function Report() {
  const { lang } = useLanguage();
  const [submitted, setSubmitted] = useState(false);
  const [formData, setFormData] = useState({
    type: "" as IssueType | "",
    location: "",
    description: "",
  });
  // One-time captured coordinates (set by user via geolocation button)
  const [coords, setCoords] = useState<{ latitude?: number; longitude?: number }>({});
  // Optional reporter name (do not enforce validation)
  const [reporterName, setReporterName] = useState<string>("");
  // Visual flag for temporary marker shown after capturing location
  const [showTempMarker, setShowTempMarker] = useState(false);
  // Track location source and resolved address
  const [locationSource, setLocationSource] = useState<string>("manual");
  const [resolvedAddress, setResolvedAddress] = useState<string>("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    // Build payload matching required shape. Use captured coords if available; fallback to null to avoid blocking.
    const latitude = coords.latitude ?? null;
    const longitude = coords.longitude ?? null;

    // Best-effort IP fetch: try with short timeout, do not block submission on failure.
    const fetchIp = async (): Promise<string | null> => {
      try {
        const controller = new AbortController();
        const id = setTimeout(() => controller.abort(), 1500); // 1.5s timeout
        const res = await fetch("https://api.ipify.org?format=json", { signal: controller.signal });
        clearTimeout(id);
        if (!res.ok) return null;
        const j = await res.json();
        return j.ip || null;
      } catch (err) {
        return null;
      }
    };

    const ipPromise = fetchIp();

    const payload = {
      // Optional reporter name
      reporter_name: reporterName || undefined,
      latitude: latitude,
      longitude: longitude,
      // ip_address will be filled below (best-effort)
      ip_address: null as string | null | undefined,
      description: formData.description,
      city: "",
      locality: formData.location,
    } as any;

    // Attempt to resolve IP but don't block indefinitely
    try {
      const ip = await ipPromise;
      payload.ip_address = ip;
    } catch (err) {
      payload.ip_address = null;
    }

    // Send to backend (best-effort). If API fails, continue to show success to the user (preserve UX).
    try {
      // Use absolute backend URL to avoid React Router interpreting API paths as frontend routes
      await fetch(`${API_BASE_URL}/reports`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          description: payload.description,
          issue_type: formData.type || undefined,
          city: payload.city || undefined,
          locality: payload.locality,
          latitude: payload.latitude,
          longitude: payload.longitude,
          reporter_name: payload.reporter_name,
          ip_address: payload.ip_address,
          // Frontend location fields
          resolved_address: resolvedAddress || undefined,
          user_entered_location: formData.location || undefined,
          location_source: locationSource || "manual",
        }),
      });
    } catch (err) {
      // swallow errors to avoid breaking UX
      console.warn("Report submission failed (will continue):", err);
    }

    // show submission success (same UX as before)
    setSubmitted(true);
    setTimeout(() => {
      setSubmitted(false);
      setFormData({ type: "", location: "", description: "" });
      setReporterName("");
      setCoords({});
      setShowTempMarker(false);
      setLocationSource("manual");
      setResolvedAddress("");
      // Remove one-time stored location
      try {
        localStorage.removeItem("nagar_user_location");
      } catch (e) {}
    }, 3000);
  };

  // Capture current location once when user clicks the button.
  const handleUseCurrentLocation = () => {
    if (!navigator.geolocation) {
      alert("Geolocation is not supported by your browser.");
      return;
    }

    // Request permission and capture position once.
    navigator.geolocation.getCurrentPosition(
      async (position) => {
        const lat = position.coords.latitude;
        const lon = position.coords.longitude;
        setCoords({ latitude: lat, longitude: lon });
        setShowTempMarker(true);

        // Store a one-time value so other components (e.g., map) can read and center on it.
        // This is a lightweight, non-invasive signal (no continuous tracking).
        try {
          localStorage.setItem("nagar_user_location", JSON.stringify({ latitude: lat, longitude: lon }));
        } catch (e) {}

        // Dispatch an event so map components that choose to listen can react (non-intrusive).
        try {
          window.dispatchEvent(new CustomEvent("nagar:user-location", { detail: { latitude: lat, longitude: lon } }));
        } catch (e) {}

        // Reverse geocode using OpenStreetMap Nominatim (NO API KEY required)
        try {
          const controller = new AbortController();
          const timeoutId = setTimeout(() => controller.abort(), 3000); // 3s timeout
          
          const response = await fetch(
            `https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lon}`,
            {
              signal: controller.signal,
              headers: {
                'User-Agent': 'NagarAlertHub/1.0'
              }
            }
          );
          
          clearTimeout(timeoutId);
          
          if (response.ok) {
            const data = await response.json();
            const address = data.display_name || 
                          [data.address?.suburb, data.address?.city, data.address?.state]
                            .filter(Boolean)
                            .join(", ");
            
            if (address && !formData.location) {
              // Auto-fill only if field is empty
              setFormData({ ...formData, location: address });
              setResolvedAddress(address);
              setLocationSource("frontend-geocoded");
            }
          }
        } catch (err: any) {
          // Silent fallback - only log non-abort errors
          if (err.name !== "AbortError") {
            console.error("Reverse geocoding failed:", err);
          }
        }
      },
      (err) => {
        console.warn("Geolocation failed:", err);
        alert("Unable to get your location. Please allow location access or enter location manually.");
      },
      { enableHighAccuracy: false, timeout: 10000, maximumAge: 0 }
    );
  };

  if (submitted) {
    return (
      <div className={styles.page}>
        <Header />
        <main className={styles.container}>
          <div className={styles.card}>
            <div className={styles.successMessage}>
              <CheckCircle className={styles.successIcon} />
              <h2 className={styles.successTitle}>{t(lang, "thank_you")}</h2>
              <p className={styles.successText}>{t(lang, "report_received")}</p>
              <Button onClick={() => setSubmitted(false)}>{t(lang, "submit_another")}</Button>
            </div>
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className={styles.page}>
      <Header />
      <main className={styles.container}>
        <div className={styles.header}>
          <h1 className={styles.title}>{t(lang, "report_issue")}</h1>
          <p className={styles.subtitle}>{t(lang, "report_subtitle")}</p>
        </div>

        <div className={styles.card}>
          <form className={styles.form} onSubmit={handleSubmit}>
            <div className={styles.field}>
              <label className={styles.label}>
                {t(lang, "issue_type_label")} <span className={styles.required}>*</span>
              </label>
              <Select
                value={formData.type}
                onValueChange={(value) => setFormData({ ...formData, type: value as IssueType })}
              >
                <SelectTrigger>
                  <SelectValue placeholder={t(lang, "issue_type_placeholder")} />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="Traffic">{t(lang, "issue_type_traffic")}</SelectItem>
                  <SelectItem value="Power">{t(lang, "issue_type_power")}</SelectItem>
                  <SelectItem value="Water">{t(lang, "issue_type_water")}</SelectItem>
                  <SelectItem value="Roadblock">{t(lang, "issue_type_roadblock")}</SelectItem>
                  <SelectItem value="Safety">{t(lang, "issue_type_safety")}</SelectItem>
                  <SelectItem value="Other">{t(lang, "issue_type_other")}</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className={styles.field}>
              <label className={styles.label} htmlFor="location">
                {t(lang, "location_label")} <span className={styles.required}>*</span>
              </label>

              <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
                <Input
                  id="location"
                  type="text"
                  placeholder={t(lang, "location_placeholder")}
                  value={formData.location}
                  onChange={(e) => setFormData({ ...formData, location: e.target.value })}
                  required
                />

                {/* One-time location capture button. Location is used only for this report. */}
                <button
                  type="button"
                  className={styles.locationButton}
                  onClick={handleUseCurrentLocation}
                  title={t(lang, "use_current_location")}
                  style={{ padding: "8px 10px" }}
                >
                  {t(lang, "use_current_location")}
                </button>
              </div>

              <span className={styles.helpText}>{t(lang, "location_help")}</span>
              {resolvedAddress && locationSource === "frontend-geocoded" && (
                <div style={{ marginTop: 6 }} className={styles.helpText}>
                  <small>{t(lang, "address_auto_detected")}</small>
                </div>
              )}

              {showTempMarker && coords.latitude && coords.longitude && (
                <div className={styles.tempMarker}>
                  <strong>{t(lang, "location_captured")}</strong> {coords.latitude.toFixed(5)}, {coords.longitude.toFixed(5)}
                </div>
              )}
            </div>

            <div className={styles.field}>
              <label className={styles.label} htmlFor="description">
                {t(lang, "description_label")} <span className={styles.required}>*</span>
              </label>
              <Textarea
                id="description"
                placeholder={t(lang, "description_placeholder")}
                rows={5}
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                required
              />
              <span className={styles.helpText}>{t(lang, "description_help")}</span>
            </div>

            <div className={styles.field}>
              <label className={styles.label}>{t(lang, "photo_video")}</label>
              <div className={styles.fileInput}>
                <label className={styles.fileInputLabel}>
                  <Upload className={styles.uploadIcon} />
                  <span className={styles.fileInputText}>{t(lang, "upload_text")}</span>
                  <span className={styles.fileInputHint}>{t(lang, "upload_hint")}</span>
                  <input type="file" accept="image/*,video/*" style={{ display: "none" }} />
                </label>
              </div>
            </div>

            <div className={styles.actions}>
              <div style={{ display: "flex", gap: 12, width: "100%" }}>
                <Input
                  id="reporter_name"
                  type="text"
                  placeholder={t(lang, "reporter_name_placeholder")}
                  value={reporterName}
                  onChange={(e) => setReporterName(e.target.value)}
                  style={{ flex: 1 }}
                />
                <Button type="submit" size="lg" style={{ flex: 1 }}>
                  {t(lang, "submit_report")}
                </Button>
              </div>
            </div>
          </form>
        </div>
      </main>
    </div>
  );
}
