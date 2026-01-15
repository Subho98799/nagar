import { useState, useEffect } from "react";
import { X, ThumbsUp, ThumbsDown, MessageCircle, Send } from "lucide-react";
import { Button } from "~/components/ui/button/button";
import { Input } from "~/components/ui/input/input";
import { Textarea } from "~/components/ui/textarea/textarea";
import {
  getIssueAnalytics,
  getIssueComments,
  addComment,
  voteOnIssue,
  getIssueVotes,
  type TimelineIssue,
  type IssueAnalytics,
  type Comment,
} from "~/lib/timeline-api";
import { getCurrentUser } from "~/lib/auth";
import { AnalyticsCharts } from "./analytics-charts";
import styles from "./issue-side-panel.module.css";

interface IssueSidePanelProps {
  issue: TimelineIssue;
  onClose: () => void;
  onVoteUpdate: (issueId: string, updatedIssue: TimelineIssue) => void;
}

export function IssueSidePanel({ issue, onClose, onVoteUpdate }: IssueSidePanelProps) {
  const [analytics, setAnalytics] = useState<IssueAnalytics | null>(null);
  const [comments, setComments] = useState<Comment[]>([]);
  const [loading, setLoading] = useState(true);
  const [commentText, setCommentText] = useState("");
  const [submittingComment, setSubmittingComment] = useState(false);
  const [voting, setVoting] = useState(false);
  const [localVotes, setLocalVotes] = useState({ upvotes: issue.upvotes, downvotes: issue.downvotes });
  const [userVote, setUserVote] = useState<"upvote" | "downvote" | null>(issue.user_vote || null);

  useEffect(() => {
    loadData();
  }, [issue.id]);

  const loadData = async () => {
    setLoading(true);
    try {
      const [analyticsData, commentsData] = await Promise.all([
        getIssueAnalytics(issue.id),
        getIssueComments(issue.id),
      ]);
      setAnalytics(analyticsData);
      setComments(commentsData);
    } catch (err) {
      console.error("Failed to load analytics/comments:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleVote = async (voteType: "upvote" | "downvote") => {
    if (voting) return;

    setVoting(true);
    try {
      const user = getCurrentUser();
      const result = await voteOnIssue(issue.id, voteType, user?.id);
      
      setLocalVotes({ upvotes: result.upvotes, downvotes: result.downvotes });
      setUserVote(result.user_vote || null);
      
      onVoteUpdate(issue.id, {
        ...issue,
        upvotes: result.upvotes,
        downvotes: result.downvotes,
        user_vote: result.user_vote || null,
      });
    } catch (err) {
      console.error("Failed to vote:", err);
    } finally {
      setVoting(false);
    }
  };

  const handleAddComment = async () => {
    if (!commentText.trim() || submittingComment) return;

    setSubmittingComment(true);
    try {
      const user = getCurrentUser();
      const newComment = await addComment(issue.id, commentText, user?.id);
      setComments([newComment, ...comments]);
      setCommentText("");
      
      // Update comment count
      onVoteUpdate(issue.id, {
        ...issue,
        comment_count: comments.length + 1,
      });
    } catch (err) {
      console.error("Failed to add comment:", err);
    } finally {
      setSubmittingComment(false);
    }
  };

  return (
    <div className={styles.overlay} onClick={onClose}>
      <div className={styles.panel} onClick={(e) => e.stopPropagation()}>
        <div className={styles.header}>
          <h2 className={styles.title}>Issue Details</h2>
          <Button variant="ghost" size="icon" onClick={onClose} className={styles.closeButton}>
            <X className={styles.closeIcon} />
          </Button>
        </div>

        <div className={styles.content}>
          {loading ? (
            <div className={styles.loading}>Loading analytics...</div>
          ) : (
            <>
              {/* Issue Summary */}
              <section className={styles.section}>
                <h3 className={styles.sectionTitle}>{issue.title}</h3>
                <p className={styles.description}>{issue.description}</p>
                
                <div className={styles.metrics}>
                  <div className={styles.metric}>
                    <span className={styles.metricLabel}>Popularity</span>
                    <span className={styles.metricValue}>{Math.round(issue.popularity_score)}</span>
                  </div>
                  <div className={styles.metric}>
                    <span className={styles.metricLabel}>Confidence</span>
                    <span className={styles.metricValue}>{issue.confidence}</span>
                  </div>
                  {issue.priority_score !== undefined && (
                    <div className={styles.metric}>
                      <span className={styles.metricLabel}>Priority</span>
                      <span className={styles.metricValue}>{issue.priority_score}</span>
                    </div>
                  )}
                </div>
              </section>

              {/* Voting */}
              <section className={styles.section}>
                <div className={styles.voting}>
                  <Button
                    variant={userVote === "upvote" ? "default" : "outline"}
                    onClick={() => handleVote("upvote")}
                    disabled={voting}
                    className={styles.voteButton}
                  >
                    <ThumbsUp className={styles.voteIcon} />
                    <span>{localVotes.upvotes}</span>
                  </Button>
                  <Button
                    variant={userVote === "downvote" ? "destructive" : "outline"}
                    onClick={() => handleVote("downvote")}
                    disabled={voting}
                    className={styles.voteButton}
                  >
                    <ThumbsDown className={styles.voteIcon} />
                    <span>{localVotes.downvotes}</span>
                  </Button>
                </div>
              </section>

              {/* Analytics Charts */}
              {analytics && (
                <section className={styles.section}>
                  <h3 className={styles.sectionTitle}>Analytics</h3>
                  <AnalyticsCharts analytics={analytics} issue={issue} />
                </section>
              )}

              {/* Sources */}
              {analytics && analytics.sources.length > 0 && (
                <section className={styles.section}>
                  <h3 className={styles.sectionTitle}>Sources</h3>
                  <div className={styles.sources}>
                    {analytics.sources.map((source, idx) => (
                      <div key={idx} className={styles.source}>
                        <span className={styles.sourceType}>{source.source_type}</span>
                        <span className={styles.sourceCount}>{source.count} reports</span>
                      </div>
                    ))}
                  </div>
                </section>
              )}

              {/* Comments */}
              <section className={styles.section}>
                <h3 className={styles.sectionTitle}>Comments ({comments.length})</h3>
                
                <div className={styles.commentForm}>
                  <Textarea
                    placeholder="Add a comment..."
                    value={commentText}
                    onChange={(e) => setCommentText(e.target.value)}
                    className={styles.commentInput}
                    rows={3}
                  />
                  <Button
                    onClick={handleAddComment}
                    disabled={!commentText.trim() || submittingComment}
                    className={styles.commentSubmit}
                  >
                    <Send className={styles.commentIcon} />
                    <span>Post</span>
                  </Button>
                </div>

                <div className={styles.comments}>
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
                      </div>
                    ))
                  )}
                </div>
              </section>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
