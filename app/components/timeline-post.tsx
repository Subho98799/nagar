import { useState } from "react";
import { ThumbsUp, ThumbsDown, MessageCircle, TrendingUp, TrendingDown, MapPin, Clock, Users, AlertCircle } from "lucide-react";
import { voteOnIssue, type TimelineIssue } from "~/lib/timeline";
import { isAuthenticated } from "~/lib/auth";
import { ENABLE_SIGNAL_INPUTS } from "~/lib/config";
import { Button } from "~/components/ui/button/button";
import { Badge } from "~/components/ui/badge/badge";
import styles from "./timeline-post.module.css";

interface TimelinePostProps {
  issue: TimelineIssue;
  onClick: () => void;
  onVoteChange: () => void;
}

export function TimelinePost({ issue, onClick, onVoteChange }: TimelinePostProps) {
  const [isVoting, setIsVoting] = useState(false);
  const [localUpvotes, setLocalUpvotes] = useState(issue.upvote_count);
  const [localDownvotes, setLocalDownvotes] = useState(issue.downvote_count);
  const [userVote, setUserVote] = useState<"UPVOTE" | "DOWNVOTE" | null>(
    issue.user_vote || null
  );

  const handleVote = async (voteType: "UPVOTE" | "DOWNVOTE") => {
    if (!isAuthenticated()) {
      alert("Please login to vote");
      return;
    }

    if (isVoting) return;

    try {
      setIsVoting(true);
      const result = await voteOnIssue(issue.id, voteType);

      if (result.success) {
        setLocalUpvotes(result.upvote_count);
        setLocalDownvotes(result.downvote_count);
        setUserVote(result.user_vote === "UPVOTE" ? "UPVOTE" : result.user_vote === "DOWNVOTE" ? "DOWNVOTE" : null);
        onVoteChange();
      }
    } catch (error) {
      console.error("Failed to vote:", error);
      alert("Failed to vote. Please try again.");
    } finally {
      setIsVoting(false);
    }
  };

  const timeAgo = new Date(issue.created_at).toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });

  const confidenceColor = issue.confidence_score >= 0.7 ? "high" : issue.confidence_score >= 0.4 ? "medium" : "low";
  const popularityColor = issue.popularity_score > 0 ? "positive" : issue.popularity_score < 0 ? "negative" : "neutral";

  return (
    <article className={styles.post} onClick={onClick}>
      <div className={styles.header}>
        <div className={styles.headerLeft}>
          <Badge variant="outline" className={styles.typeBadge}>
            {issue.issue_type}
          </Badge>
          <span className={styles.time}>{timeAgo}</span>
        </div>
        <div className={styles.scores}>
          <div className={`${styles.score} ${styles[confidenceColor]}`}>
            <AlertCircle className={styles.scoreIcon} />
            <span>{(issue.confidence_score * 100).toFixed(0)}%</span>
          </div>
          {issue.priority_score !== undefined && (
            <div className={styles.score}>
              <TrendingUp className={styles.scoreIcon} />
              <span>Priority: {issue.priority_score}</span>
            </div>
          )}
        </div>
      </div>

      <h2 className={styles.title}>{issue.title}</h2>
      <p className={styles.description}>{issue.description}</p>

      {issue.locality && (
        <div className={styles.location}>
          <MapPin className={styles.locationIcon} />
          <span>{issue.locality}{issue.city ? `, ${issue.city}` : ""}</span>
        </div>
      )}

      <div className={styles.metadata}>
        <div className={styles.metaItem}>
          <Users className={styles.metaIcon} />
          <span>{issue.report_count} reports</span>
        </div>
        <div className={styles.metaItem}>
          <Clock className={styles.metaIcon} />
          <span>{issue.status}</span>
        </div>
        {issue.sources.length > 0 && (
          <div className={styles.metaItem}>
            <span>Sources: {issue.sources.map(s => s.description).join(", ")}</span>
          </div>
        )}
      </div>

      <div className={styles.actions}>
        <div className={`${styles.popularity} ${styles[popularityColor]}`}>
          {issue.popularity_score > 0 ? (
            <TrendingUp className={styles.popularityIcon} />
          ) : issue.popularity_score < 0 ? (
            <TrendingDown className={styles.popularityIcon} />
          ) : null}
          <span>Signal: {issue.popularity_score}</span>
        </div>

        {ENABLE_SIGNAL_INPUTS && (
          <>
            <Button
              variant={userVote === "UPVOTE" ? "default" : "ghost"}
              size="sm"
              onClick={(e) => {
                e.stopPropagation();
                handleVote("UPVOTE");
              }}
              disabled={isVoting}
              className={styles.actionButton}
              title="Non-authoritative signal for moderators"
            >
              <ThumbsUp className={styles.actionIcon} />
              <span>{localUpvotes}</span>
            </Button>

            <Button
              variant={userVote === "DOWNVOTE" ? "destructive" : "ghost"}
              size="sm"
              onClick={(e) => {
                e.stopPropagation();
                handleVote("DOWNVOTE");
              }}
              disabled={isVoting}
              className={styles.actionButton}
              title="Non-authoritative signal for moderators"
            >
              <ThumbsDown className={styles.actionIcon} />
              <span>{localDownvotes}</span>
            </Button>
          </>
        )}

        <Button
          variant="ghost"
          size="sm"
          onClick={(e) => {
            e.stopPropagation();
            onClick();
          }}
          className={styles.actionButton}
          title={ENABLE_SIGNAL_INPUTS ? "Open admin analytics panel" : "Admin analytics disabled"}
        >
          <MessageCircle className={styles.actionIcon} />
          <span>{issue.comment_count}</span>
        </Button>
      </div>
    </article>
  );
}
