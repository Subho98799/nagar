import { MapPin, Clock, Users, AlertCircle, CheckCircle2, HelpCircle } from "lucide-react";
import { Link } from "react-router";
import type { Issue } from "~/data/mock-issues";
import { Badge } from "~/components/ui/badge/badge";
import styles from "./issue-card.module.css";

interface IssueCardProps {
  /**
   * Issue data to display
   * @important
   */
  issue: Issue;
  className?: string;
}

const severityConfig = {
  Low: { label: "Low Impact", className: "severityLow" },
  Medium: { label: "Medium Impact", className: "severityMedium" },
  High: { label: "High Impact", className: "severityHigh" },
};

const confidenceConfig = {
  Low: { icon: HelpCircle, className: "low" },
  Medium: { icon: AlertCircle, className: "medium" },
  High: { icon: CheckCircle2, className: "high" },
};

/**
 * Card component displaying issue summary
 */
export function IssueCard({ issue, className }: IssueCardProps) {
  const timeAgo = new Date(issue.timestamp).toLocaleTimeString("en-US", {
    hour: "2-digit",
    minute: "2-digit",
  });

  return (
    <Link to={`/issue/${issue.id}`} className={`${styles.card} ${className || ""}`}>
      <div className={styles.header}>
        <div className={styles.titleSection}>
          <h3 className={styles.title}>{issue.title}</h3>
          <div className={styles.location}>
            <MapPin className={styles.locationIcon} />
            <span>{issue.location}</span>
          </div>
        </div>
        <Badge variant="outline">{issue.type}</Badge>
      </div>

      <p className={styles.description}>{issue.description}</p>

      <div className={styles.footer}>
        <div className={styles.metadata}>
          <div className={styles.metaItem}>
            <Clock className={styles.metaIcon} />
            <span>{timeAgo}</span>
          </div>
          <div className={styles.metaItem}>
            <Users className={styles.metaIcon} />
            <span>{issue.reportCount} reports</span>
          </div>
          <div className={`${styles.metaItem} ${styles[severityConfig[issue.severity].className]}`}>
            <AlertCircle className={styles.metaIcon} />
            <span>{severityConfig[issue.severity].label}</span>
          </div>
        </div>
        <div className={`${styles.confidenceBadge} ${styles[confidenceConfig[issue.confidence].className]}`}>
          {(() => {
            const Icon = confidenceConfig[issue.confidence].icon;
            return <Icon className={styles.confidenceIcon} />;
          })()}
          <span>{issue.confidence} Confidence</span>
        </div>
      </div>
    </Link>
  );
}
