import { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { Header } from "~/components/header";
import { TimelinePost } from "~/components/timeline-post";
import { IssueAnalyticsPanel } from "~/components/issue-analytics-panel";
import { fetchTimelineFeed, type TimelineIssue } from "~/lib/timeline";
import { isAuthenticated } from "~/lib/auth";
import { useNavigate } from "react-router";
import styles from "./timeline.module.css";

export default function Timeline() {
  const { t } = useTranslation();
  const [issues, setIssues] = useState<TimelineIssue[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedIssueId, setSelectedIssueId] = useState<string | null>(null);
  const [showAnalytics, setShowAnalytics] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    // Redirect to login if not authenticated
    if (!isAuthenticated()) {
      navigate("/login");
      return;
    }

    loadTimeline();
  }, [navigate]);

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
    setSelectedIssueId(issueId);
    setShowAnalytics(true);
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
          <div className={styles.loading}>{t('common.loading')}</div>
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
            <h1 className={styles.title}>{t('timeline.title')}</h1>
            <p className={styles.subtitle}>{t('timeline.events')}</p>
          </div>

          <div className={styles.feed}>
            {issues.length === 0 ? (
              <div className={styles.empty}>
                <p>{t('timeline.noEvents')}</p>
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
          </div>
        </div>

        {showAnalytics && selectedIssueId && (
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
