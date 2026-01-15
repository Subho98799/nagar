import { lazy, Suspense, useEffect, useState } from "react";
import { Header } from "~/components/header";
import { mockIssues } from "~/data/mock-issues";
import { fetchIssues } from "~/lib/api";
import styles from "./map.module.css";

const CityMap = lazy(() => import("~/components/city-map").then(m => ({ default: m.CityMap })));

export default function MapPage() {
  const [issues, setIssues] = useState<typeof mockIssues>(mockIssues);

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
        if (mounted) setIssues(mockIssues);
      }
    }).catch(() => {
      if (mounted) setIssues(mockIssues);
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
          <h1 className={styles.title}>Live Disruption Map</h1>
          <p className={styles.description}>
            Real-time visualization of all reported disruptions across the city. Click on pulsing markers to view
            detailed information about each incident.
          </p>
          <div className={styles.stats}>
            <div className={styles.stat}>
              <span className={styles.statValue}>{activeIssues.length}</span>
              <span className={styles.statLabel}>Active Disruptions</span>
            </div>
            <div className={styles.stat}>
              <span className={styles.statValue}>{activeIssues.filter((i) => i.severity === "High").length}</span>
              <span className={styles.statLabel}>High Severity</span>
            </div>
            <div className={styles.stat}>
              <span className={styles.statValue}>
                {activeIssues.reduce((sum, issue) => sum + issue.reportCount, 0)}
              </span>
              <span className={styles.statLabel}>Total Reports</span>
            </div>
          </div>
        </div>

        <Suspense fallback={<div className={styles.mapPlaceholder}>Loading map...</div>}>
          <CityMap issues={issues} className={styles.map} />
        </Suspense>

        <div className={styles.legend}>
          <h3 className={styles.legendTitle}>Severity Indicators</h3>
          <div className={styles.legendItems}>
            <div className={styles.legendItem}>
              <span className={`${styles.legendMarker} ${styles.high}`}></span>
              <span>High Severity - Immediate attention required</span>
            </div>
            <div className={styles.legendItem}>
              <span className={`${styles.legendMarker} ${styles.medium}`}></span>
              <span>Medium Severity - Monitoring ongoing</span>
            </div>
            <div className={styles.legendItem}>
              <span className={`${styles.legendMarker} ${styles.low}`}></span>
              <span>Low Severity - Minor disruption</span>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
