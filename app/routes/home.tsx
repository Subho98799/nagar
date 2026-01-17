import { useState, lazy, Suspense, useEffect } from "react";
import { CheckCircle } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Header } from "~/components/header";
import { CityPulse } from "~/components/city-pulse";
import { IssueCard } from "~/components/issue-card";
import { mockIssues } from "~/data/mock-issues";
import { USE_MOCK } from "~/lib/config";
import type { Status } from "~/data/mock-issues";
import { fetchIssues } from "~/lib/api";
import styles from "./home.module.css";

const CityMap = lazy(() => import("~/components/city-map").then(m => ({ default: m.CityMap })));

export default function Home() {
  const { t } = useTranslation();
  const [statusFilter, setStatusFilter] = useState<Status | "All">("All");
  const [issues, setIssues] = useState<typeof mockIssues>(mockIssues);

  useEffect(() => {
    let mounted = true;
    if (USE_MOCK) {
      if (mounted) setIssues(mockIssues as any);
      return () => {
        mounted = false;
      };
    }

    fetchIssues()
      .then((serverIssues) => {
        // Simple mapping same as map.tsx
        const mapped = serverIssues.map((s) => ({
          id: s.id,
          type: ((): any => {
            const it = s.issue_type || "";
            if (/traffic|road/i.test(it)) return "Traffic";
            if (/power|electric/i.test(it)) return "Power";
            if (/water/i.test(it)) return "Water";
            if (/infrastructure|roadblock|bridge/i.test(it)) return "Roadblock";
            if (/safety|crime|security/i.test(it)) return "Safety";
            return "Other";
          })(),
          title: s.title,
          location: s.locality ? `${s.locality}, ${s.city || ""}`.trim().replace(/, $/, "") : s.city || "",
          description: s.description,
          severity: (s.severity || "Low") as any,
          confidence: (s.confidence === "HIGH" ? "High" : s.confidence === "MEDIUM" ? "Medium" : "Low") as any,
          status: s.status === "CONFIRMED" ? "Active" : s.status === "RESOLVED" ? "Resolved" : "Under Review",
          timestamp: s.created_at || new Date().toISOString(),
          reportCount: s.report_count || 1,
          timeline: [
            {
              id: `${s.id}-t1`,
              timestamp: s.created_at || new Date().toISOString(),
              time: new Date(s.created_at || new Date().toISOString()).toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" }),
              confidence: (s.confidence === "HIGH" ? "High" : s.confidence === "MEDIUM" ? "Medium" : "Low") as any,
              description: s.description || "",
            },
          ],
          operatorNotes: s.operatorNotes,
        }));

        if (mounted) setIssues(mapped as any);
      })
      .catch((err) => {
        // Do not fallback to mock automatically. Log and show empty state.
        // eslint-disable-next-line no-console
        console.error("fetchIssues failed:", err);
        if (mounted) setIssues([] as any);
      });

    return () => {
      mounted = false;
    };
  }, []);

  const filteredIssues = statusFilter === "All" ? issues : issues.filter((issue) => issue.status === statusFilter);

  return (
    <div className={styles.page}>
      <Header />
      <main className={styles.container}>
        <CityPulse issues={issues} className={styles.cityPulse} />

        <div className={styles.filters}>
          {(["All", "Active", "Under Review", "Resolved"] as const).map((status) => (
            <button
              key={status}
              className={`${styles.filterButton} ${statusFilter === status ? styles.active : ""}`}
              onClick={() => setStatusFilter(status)}
            >
              {status === "All" ? t('home.allStatuses') : t(`home.status.${status.toLowerCase().replace(' ', '')}`)}
            </button>
          ))}
        </div>

        {filteredIssues.length > 0 ? (
          <div className={styles.issuesGrid}>
            {filteredIssues.map((issue) => (
              <IssueCard key={issue.id} issue={issue} />
            ))}
          </div>
        ) : (
          <div className={styles.empty}>
            <CheckCircle className={styles.emptyIcon} />
            <h3 className={styles.emptyTitle}>{t('home.noAlerts')}</h3>
            <p>{t('home.noIssuesMessage', { status: statusFilter.toLowerCase() })}</p>
          </div>
        )}

        <section className={styles.mapSection}>
          <h2 className={styles.sectionTitle}>{t('home.cityHealth')}</h2>
          <p className={styles.sectionDescription}>
            {t('home.mapDescription')}
          </p>
          <Suspense fallback={<div className={styles.mapPlaceholder}>{t('common.loading')}</div>}>
            <CityMap issues={issues} />
          </Suspense>
        </section>
      </main>
    </div>
  );
}
