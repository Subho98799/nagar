import { useState, useEffect } from "react";
import { X, ThumbsUp, ThumbsDown, MessageCircle, TrendingUp, AlertCircle, MapPin } from "lucide-react";
import { fetchIssueAnalytics, addComment, fetchIssueComments, type IssueAnalytics, type Comment } from "~/lib/timeline";
import { isAuthenticated } from "~/lib/auth";
import { Button } from "~/components/ui/button/button";
import { Textarea } from "~/components/ui/textarea/textarea";
import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, LineChart, Line } from "recharts";
import { Suspense, lazy } from "react";
import styles from "./issue-analytics-panel.module.css";

// Lazy load map component to avoid SSR issues with Leaflet
const LocationHeatmapMap = lazy(() => 
  import("./location-heatmap-map").then(m => ({ default: m.LocationHeatmapMap }))
);

interface IssueAnalyticsPanelProps {
  issueId: string;
  onClose: () => void;
  onCommentAdded: () => void;
}

const COLORS = ["#0088FE", "#00C49F", "#FFBB28", "#FF8042", "#8884d8"];

export function IssueAnalyticsPanel({ issueId, onClose, onCommentAdded }: IssueAnalyticsPanelProps) {
  const [analytics, setAnalytics] = useState<IssueAnalytics | null>(null);
  const [loading, setLoading] = useState(true);
  const [comments, setComments] = useState<Comment[]>([]);
  const [commentText, setCommentText] = useState("");
  const [submittingComment, setSubmittingComment] = useState(false);

  useEffect(() => {
    loadAnalytics();
    loadComments();
  }, [issueId]);

  const loadAnalytics = async () => {
    try {
      setLoading(true);
      const data = await fetchIssueAnalytics(issueId);
      setAnalytics(data);
    } catch (error) {
      console.error("Failed to load analytics:", error);
    } finally {
      setLoading(false);
    }
  };

  const loadComments = async () => {
    try {
      const data = await fetchIssueComments(issueId);
      setComments(data);
    } catch (error) {
      console.error("Failed to load comments:", error);
    }
  };

  const handleSubmitComment = async () => {
    if (!commentText.trim() || !isAuthenticated()) {
      alert("Please login to comment");
      return;
    }

    try {
      setSubmittingComment(true);
      await addComment(issueId, commentText);
      setCommentText("");
      await loadComments();
      onCommentAdded();
    } catch (error) {
      console.error("Failed to add comment:", error);
      alert("Failed to add comment. Please try again.");
    } finally {
      setSubmittingComment(false);
    }
  };

  if (loading) {
    return (
      <div className={styles.panel}>
        <div className={styles.header}>
          <h2>Analytics</h2>
          <Button variant="ghost" size="sm" onClick={onClose}>
            <X />
          </Button>
        </div>
        <div className={styles.loading}>Loading analytics...</div>
      </div>
    );
  }

  if (!analytics) {
    return (
      <div className={styles.panel}>
        <div className={styles.header}>
          <h2>Analytics</h2>
          <Button variant="ghost" size="sm" onClick={onClose}>
            <X />
          </Button>
        </div>
        <div className={styles.error}>Failed to load analytics</div>
      </div>
    );
  }

  // Prepare data for charts
  const sourceData = Object.entries(analytics.source_breakdown).map(([name, value]) => ({
    name,
    value,
  }));

  const severityData = Object.entries(analytics.severity_distribution).map(([name, value]) => ({
    name,
    value,
  }));

  const reportsTimeData = analytics.reports_over_time.map((item) => ({
    date: new Date(item.date).toLocaleDateString("en-US", { month: "short", day: "numeric" }),
    count: item.count,
  }));

  const votesTimeData = analytics.votes_over_time.map((item) => ({
    date: new Date(item.date).toLocaleDateString("en-US", { month: "short", day: "numeric" }),
    upvotes: item.upvotes,
    downvotes: item.downvotes,
  }));

  const confidenceTimeData = analytics.confidence_over_time.map((item) => ({
    date: new Date(item.date).toLocaleDateString("en-US", { month: "short", day: "numeric" }),
    confidence: (item.confidence * 100).toFixed(0),
  }));

  return (
    <div className={styles.panel}>
      <div className={styles.header}>
        <h2>Issue Analytics</h2>
        <Button variant="ghost" size="sm" onClick={onClose}>
          <X />
        </Button>
      </div>

      <div className={styles.content}>
        {/* Scores Section */}
        <section className={styles.section}>
          <h3 className={styles.sectionTitle}>Scores</h3>
          <div className={styles.scoresGrid}>
            <div className={styles.scoreCard}>
              <TrendingUp className={styles.scoreIcon} />
              <div>
                <div className={styles.scoreLabel}>Popularity</div>
                <div className={styles.scoreValue}>{analytics.popularity_score}</div>
              </div>
            </div>
            <div className={styles.scoreCard}>
              <AlertCircle className={styles.scoreIcon} />
              <div>
                <div className={styles.scoreLabel}>Confidence</div>
                <div className={styles.scoreValue}>{(analytics.confidence_score * 100).toFixed(0)}%</div>
              </div>
            </div>
            {analytics.priority_score !== undefined && (
              <div className={styles.scoreCard}>
                <TrendingUp className={styles.scoreIcon} />
                <div>
                  <div className={styles.scoreLabel}>Priority</div>
                  <div className={styles.scoreValue}>{analytics.priority_score}</div>
                </div>
              </div>
            )}
          </div>
        </section>

        {/* Source Breakdown Pie Chart */}
        {sourceData.length > 0 && (
          <section className={styles.section}>
            <h3 className={styles.sectionTitle}>Source Breakdown</h3>
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={sourceData}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                  outerRadius={80}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {sourceData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </section>
        )}

        {/* Reports Over Time */}
        {reportsTimeData.length > 0 && (
          <section className={styles.section}>
            <h3 className={styles.sectionTitle}>Reports Over Time</h3>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={reportsTimeData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" />
                <YAxis />
                <Tooltip />
                <Legend />
                <Bar dataKey="count" fill="#8884d8" />
              </BarChart>
            </ResponsiveContainer>
          </section>
        )}

        {/* Votes Over Time */}
        {votesTimeData.length > 0 && (
          <section className={styles.section}>
            <h3 className={styles.sectionTitle}>Votes Over Time</h3>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={votesTimeData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" />
                <YAxis />
                <Tooltip />
                <Legend />
                <Line type="monotone" dataKey="upvotes" stroke="#00C49F" strokeWidth={2} />
                <Line type="monotone" dataKey="downvotes" stroke="#FF8042" strokeWidth={2} />
              </LineChart>
            </ResponsiveContainer>
          </section>
        )}

        {/* Confidence Over Time */}
        {confidenceTimeData.length > 0 && (
          <section className={styles.section}>
            <h3 className={styles.sectionTitle}>Confidence Over Time</h3>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={confidenceTimeData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" />
                <YAxis />
                <Tooltip />
                <Line type="monotone" dataKey="confidence" stroke="#0088FE" strokeWidth={2} />
              </LineChart>
            </ResponsiveContainer>
          </section>
        )}

        {/* Location Heatmap */}
        {analytics.location_heatmap.length > 0 && (
          <section className={styles.section}>
            <h3 className={styles.sectionTitle}>Location Heatmap</h3>
            <div className={styles.mapContainer}>
              <Suspense fallback={<div className={styles.mapPlaceholder}>Loading map...</div>}>
                <LocationHeatmapMap points={analytics.location_heatmap} />
              </Suspense>
            </div>
          </section>
        )}

        {/* AI Metadata */}
        {analytics.ai_metadata && (
          <section className={styles.section}>
            <h3 className={styles.sectionTitle}>AI Analysis</h3>
            <div className={styles.aiMetadata}>
              {analytics.ai_metadata.ai_classified_category && (
                <div className={styles.aiItem}>
                  <strong>Category:</strong> {analytics.ai_metadata.ai_classified_category}
                </div>
              )}
              {analytics.ai_metadata.severity_hint && (
                <div className={styles.aiItem}>
                  <strong>Severity:</strong> {analytics.ai_metadata.severity_hint}
                </div>
              )}
              {analytics.ai_metadata.keywords && analytics.ai_metadata.keywords.length > 0 && (
                <div className={styles.aiItem}>
                  <strong>Keywords:</strong> {analytics.ai_metadata.keywords.join(", ")}
                </div>
              )}
              {analytics.ai_metadata.summary && (
                <div className={styles.aiItem}>
                  <strong>Summary:</strong> {analytics.ai_metadata.summary}
                </div>
              )}
            </div>
          </section>
        )}

        {/* Comments Section */}
        <section className={styles.section}>
          <h3 className={styles.sectionTitle}>
            Comments ({analytics.total_comments})
          </h3>

          {isAuthenticated() && (
            <div className={styles.commentForm}>
              <Textarea
                placeholder="Add a comment..."
                value={commentText}
                onChange={(e) => setCommentText(e.target.value)}
                className={styles.commentInput}
              />
              <Button
                onClick={handleSubmitComment}
                disabled={!commentText.trim() || submittingComment}
                size="sm"
              >
                {submittingComment ? "Posting..." : "Post Comment"}
              </Button>
            </div>
          )}

          <div className={styles.commentsList}>
            {comments.length === 0 ? (
              <p className={styles.noComments}>No comments yet. Be the first to comment!</p>
            ) : (
              comments.map((comment) => (
                <div key={comment.id} className={styles.comment}>
                  <div className={styles.commentHeader}>
                    <span className={styles.commentAuthor}>
                      {comment.user_phone || "Anonymous"}
                    </span>
                    <span className={styles.commentTime}>
                      {new Date(comment.created_at).toLocaleString()}
                    </span>
                  </div>
                  <p className={styles.commentText}>{comment.text}</p>
                  <div className={styles.commentActions}>
                    <Button variant="ghost" size="sm">
                      <ThumbsUp className={styles.commentActionIcon} />
                      {comment.upvote_count}
                    </Button>
                    <Button variant="ghost" size="sm">
                      <ThumbsDown className={styles.commentActionIcon} />
                      {comment.downvote_count}
                    </Button>
                  </div>
                </div>
              ))
            )}
          </div>
        </section>
      </div>
    </div>
  );
}
