import { lazy, Suspense, useEffect, useState } from "react";
import { Header } from "~/components/header";
import { mockIssues } from "~/data/mock-issues";
import { fetchIssues } from "~/lib/api";
import { useLanguage } from "~/context/LanguageContext";
import { t } from "~/lib/i18n";
import styles from "./map.module.css";

const CityMap = lazy(() => import("~/components/city-map").then(m => ({ default: m.CityMap })));

export default function MapPage() {
  const { lang } = useLanguage();
  const [issues, setIssues] = useState<typeof mockIssues>([]);

  useEffect(() => {
    let mounted = true;
    fetchIssues().then((serverIssues) => {
      try {
        // Map server schema to frontend mock shape
        const mapped = serverIssues.map((s) => {
          const issueType = (() => {
            const it = s.issue_type || "";
            if (/traffic|road/i.test(it)) return "Traffic";
            if (/power|electric/i.test(it)) return "Power";
            if (/water/i.test(it)) return "Water";
            if (/infrastructure|roadblock|bridge/i.test(it)) return "Roadblock";
            if (/safety|crime|security/i.test(it)) return "Safety";
            return "Other";
          })();

          const confidenceMap = (c: string) => {
            if (c === "HIGH" || c === "High") return "High";
            if (c === "MEDIUM" || c === "Medium") return "Medium";
            return "Low";
          };

          const timestamp = s.created_at || new Date().toISOString();

          return {
            id: s.id,
            type: issueType,
            title: s.title,
            location: s.locality ? `${s.locality}, ${s.city || ""}`.trim().replace(/, $/, "") : s.city || "",
            description: s.description,
            severity: s.severity as any,
            confidence: confidenceMap(s.confidence) as any,
            status: s.status === "CONFIRMED" ? "Active" : s.status === "RESOLVED" ? "Resolved" : "Under Review",
            timestamp: timestamp,
            reportCount: s.report_count || 1,
            // CRITICAL FIX: Include actual coordinates from server
            latitude: s.latitude !== undefined ? Number(s.latitude) : undefined,
            longitude: s.longitude !== undefined ? Number(s.longitude) : undefined,
            timeline: [
              {
                id: `${s.id}-t1`,
                timestamp: timestamp,
                time: new Date(timestamp).toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" }),
                confidence: confidenceMap(s.confidence) as any,
                description: s.description || "",
              },
            ],
            operatorNotes: (s as any).operatorNotes || undefined,
          };
        });

        if (mounted) setIssues(mapped as any);
      } catch (e) {
        // Do not fallback to mock - show empty state
        console.error("Error mapping issues:", e);
        if (mounted) setIssues([] as any);
      }
    }).catch((err) => {
      // Do not fallback to mock - show empty state
      console.error("fetchIssues failed:", err);
      if (mounted) setIssues([] as any);
    });

    return () => {
      mounted = false;
    };
  }, []);

  const activeIssues = issues.filter((issue) => issue.status === "Active");

  return (
    <div className={styles.page}>
      <Header />
      <main className={styles.container}>
        <div className={styles.header}>
          <h1 className={styles.title}>{t(lang, "live_disruption_map")}</h1>
          <p className={styles.description}>{t(lang, "real_time_visualization")}</p>
          <div className={styles.stats}>
            <div className={styles.stat}>
              <span className={styles.statValue}>{activeIssues.length}</span>
              <span className={styles.statLabel}>{t(lang, "active_disruptions")}</span>
            </div>
            <div className={styles.stat}>
              <span className={styles.statValue}>{activeIssues.filter((i) => i.severity === "High").length}</span>
              <span className={styles.statLabel}>{t(lang, "high_severity")}</span>
            </div>
            <div className={styles.stat}>
              <span className={styles.statValue}>
                {activeIssues.reduce((sum, issue) => sum + issue.reportCount, 0)}
              </span>
              <span className={styles.statLabel}>{t(lang, "total_reports")}</span>
            </div>
          </div>
        </div>

        <Suspense fallback={<div className={styles.mapPlaceholder}>{t(lang, "loading_map")}</div>}>
          <CityMap issues={issues} className={styles.map} />
        </Suspense>

        <div className={styles.legend}>
          <h3 className={styles.legendTitle}>{t(lang, "severity_indicators")}</h3>
          <div className={styles.legendItems}>
            <div className={styles.legendItem}>
              <span className={`${styles.legendMarker} ${styles.high}`}></span>
              <span>{t(lang, "high_severity_desc")}</span>
            </div>
            <div className={styles.legendItem}>
              <span className={`${styles.legendMarker} ${styles.medium}`}></span>
              <span>{t(lang, "medium_severity_desc")}</span>
            </div>
            <div className={styles.legendItem}>
              <span className={`${styles.legendMarker} ${styles.low}`}></span>
              <span>{t(lang, "low_severity_desc")}</span>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
