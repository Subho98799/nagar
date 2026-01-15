import { Link, useParams } from "react-router";
import { useEffect, useState } from "react";
import type { Issue } from "~/data/mock-issues";
import { ArrowLeft, MapPin, Clock, Users, AlertCircle } from "lucide-react";
import { Header } from "~/components/header";
import { ConfidenceTimeline } from "~/components/confidence-timeline";
import { Badge } from "~/components/ui/badge/badge";
import { mockIssues } from "~/data/mock-issues";
import { fetchIssueById } from "~/lib/api";
import { USE_MOCK } from "~/lib/config";
import styles from "./issue.$id.module.css";

const severityVariant = {
  Low: "secondary" as const,
  Medium: "default" as const,
  High: "destructive" as const,
};

const confidenceColor = {
  Low: "var(--color-neutral-9)",
  Medium: "var(--color-warning-9)",
  High: "var(--color-success-9)",
};

export default function IssueDetail() {
  const { id } = useParams();
  // Use React state for `issue`; effects will populate it based on USE_MOCK or live fetch.
  const [issue, setIssue] = useState<Issue | undefined>(undefined);

  useEffect(() => {
    let mounted = true;
    if (USE_MOCK) {
      const found = mockIssues.find((i) => i.id === id);
      if (mounted) setIssue(found as any);
      return () => {
        mounted = false;
      };
    }

    // Live mode: fetch inside an effect. On error, log and leave undefined (shows Not Found).
    fetchIssueById(id || "")
      .then((s) => {
        if (!s) return;
        const issueType = (() => {
          const it = s.issue_type || "";
          if (/traffic|road/i.test(it)) return "Traffic";
          if (/power|electric/i.test(it)) return "Power";
          if (/water/i.test(it)) return "Water";
          if (/infrastructure|roadblock|bridge/i.test(it)) return "Roadblock";
          if (/safety|crime|security/i.test(it)) return "Safety";
          return "Other";
        })();

        const mapped = {
          id: s.id,
          type: issueType,
          title: s.title,
          location: s.locality ? `${s.locality}, ${s.city || ""}`.trim().replace(/, $/, "") : s.city || "",
          description: s.description,
          severity: s.severity as any,
          confidence: s.confidence === "HIGH" ? "High" : s.confidence === "MEDIUM" ? "Medium" : "Low",
          status: s.status === "CONFIRMED" ? "Active" : s.status === "RESOLVED" ? "Resolved" : "Under Review",
          timestamp: s.created_at || new Date().toISOString(),
          reportCount: s.report_count || 1,
          timeline: [
            {
              id: `${s.id}-t1`,
              timestamp: s.created_at || new Date().toISOString(),
              time: new Date(s.created_at || new Date().toISOString()).toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" }),
              confidence: s.confidence === "HIGH" ? "High" : s.confidence === "MEDIUM" ? "Medium" : "Low",
              description: s.description || "",
            },
          ],
          operatorNotes: (s as any).operatorNotes || undefined,
        } as any;

        if (mounted) setIssue(mapped as any);
      })
      .catch((err) => {
        // eslint-disable-next-line no-console
        console.error("fetchIssueById failed:", err);
      });

    return () => {
      mounted = false;
    };
  }, [id]);

  if (!issue) {
    return (
      <div className={styles.page}>
        <Header />
        <main className={styles.container}>
          <div className={styles.notFound}>
            <AlertCircle className={styles.notFoundIcon} />
            <h1 className={styles.notFoundTitle}>Issue Not Found</h1>
            <p>The issue you're looking for doesn't exist or has been removed.</p>
            <Link to="/" className={styles.backLink}>
              <ArrowLeft className={styles.backIcon} />
              Back to Dashboard
            </Link>
          </div>
        </main>
      </div>
    );
  }

  const timestamp = new Date(issue.timestamp).toLocaleString("en-US", {
    dateStyle: "medium",
    timeStyle: "short",
  });

  return (
    <div className={styles.page}>
      <Header />
      <main className={styles.container}>
        <Link to="/" className={styles.backLink}>
          <ArrowLeft className={styles.backIcon} />
          Back to Dashboard
        </Link>

        <div className={styles.card}>
          <div className={styles.header}>
            <div className={styles.titleSection}>
              <h1 className={styles.title}>{issue.title}</h1>
              <div className={styles.location}>
                <MapPin className={styles.locationIcon} />
                <span>{issue.location}</span>
              </div>
            </div>
            <div className={styles.badges}>
              <Badge variant={severityVariant[issue.severity]}>{issue.severity} Severity</Badge>
              <Badge variant="outline">{issue.type}</Badge>
              <Badge>{issue.status}</Badge>
            </div>
          </div>

          <p className={styles.description}>{issue.description}</p>

          <div className={styles.metadata}>
            <div className={styles.metaItem}>
              <span className={styles.metaLabel}>Reported</span>
              <span className={styles.metaValue}>
                <Clock className={styles.metaIcon} />
                {timestamp}
              </span>
            </div>
            <div className={styles.metaItem}>
              <span className={styles.metaLabel}>Citizen Reports</span>
              <span className={styles.metaValue}>
                <Users className={styles.metaIcon} />
                {issue.reportCount}
              </span>
            </div>
            <div className={styles.metaItem}>
              <span className={styles.metaLabel}>Confidence Level</span>
              <span className={styles.metaValue} style={{ color: confidenceColor[issue.confidence] }}>
                {issue.confidence}
              </span>
            </div>
          </div>
        </div>

        <ConfidenceTimeline events={issue.timeline} />

        {issue.operatorNotes && (
          <div className={styles.card}>
            <h3 style={{ marginBottom: "var(--space-3)", color: "var(--color-neutral-12)" }}>Operator Notes</h3>
            <p style={{ color: "var(--color-neutral-11)" }}>{issue.operatorNotes}</p>
          </div>
        )}
      </main>
    </div>
  );
}
