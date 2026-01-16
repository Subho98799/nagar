import { useState, useEffect } from "react";
import { Header } from "~/components/header";
import { TimelinePost } from "~/components/timeline-post";
import { IssueAnalyticsPanel } from "~/components/issue-analytics-panel";
import { fetchTimelineFeed, type TimelineIssue } from "~/lib/timeline";
import { isAuthenticated, isAdminUser } from "~/lib/auth";
import { ENABLE_ADMIN_ANALYTICS, ENABLE_TIMELINE } from "~/lib/config";
import styles from "./timeline.module.css";

export default function Timeline() {
  const [issues, setIssues] = useState<TimelineIssue[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedIssueId, setSelectedIssueId] = useState<string | null>(null);
  const [showAnalytics, setShowAnalytics] = useState(false);

  useEffect(() => {
    // Governance-first: timeline is optional and MUST NOT force authentication.
    // Anonymous/low-friction flows remain primary; auth gates only interaction signals.
    loadTimeline();
  }, []);

  const loadTimeline = async () => {
    try {
      setLoading(true);
      const data = await fetchTimelineFeed(undefined, 50);
      setIssues(data);
    } catch (error) {
      console.error("Failed to load timeline:", error);
    } finally {
      setLoading(false);
    }
  };

  const handlePostClick = (issueId: string) => {
    // Analytics/charts are admin-only (demo guardrail; not security).
    if (ENABLE_ADMIN_ANALYTICS && isAdminUser()) {
      setSelectedIssueId(issueId);
      setShowAnalytics(true);
    }
  };

  const handleCloseAnalytics = () => {
    setShowAnalytics(false);
    setSelectedIssueId(null);
  };

  if (loading) {
    return (
      <div className={styles.page}>
        <Header />
        <main className={styles.container}>
          <div className={styles.loading}>Loading timeline...</div>
        </main>
      </div>
    );
  }

  return (
    <div className={styles.page}>
      <Header />
      <main className={styles.main}>
        <div className={styles.timelineContainer}>
          <div className={styles.header}>
            <h1 className={styles.title}>Issue Timeline</h1>
            <p className={styles.subtitle}>Stay updated with all civic issues in your city</p>
          </div>

          {!ENABLE_TIMELINE && (
            <div className={styles.empty}>
              <p>
                Timeline is currently disabled for the public demo. Use the Dashboard + Map for the core civic workflow.
              </p>
            </div>
          )}

          {ENABLE_TIMELINE && !isAuthenticated() && (
            <div className={styles.empty}>
              <p>
                You can browse issues anonymously. Login is only required if you want to leave moderation signals (votes/notes).
              </p>
            </div>
          )}

          {ENABLE_TIMELINE && <div className={styles.feed}>
            {issues.length === 0 ? (
              <div className={styles.empty}>
                <p>No issues found. Be the first to report an issue!</p>
              </div>
            ) : (
              issues.map((issue) => (
                <TimelinePost
                  key={issue.id}
                  issue={issue}
                  onClick={() => handlePostClick(issue.id)}
                  onVoteChange={loadTimeline}
                />
              ))
            )}
          </div>}
        </div>

        {showAnalytics && selectedIssueId && ENABLE_ADMIN_ANALYTICS && isAdminUser() && (
          <IssueAnalyticsPanel
            issueId={selectedIssueId}
            onClose={handleCloseAnalytics}
            onCommentAdded={loadTimeline}
          />
        )}
      </main>
    </div>
  );
}
