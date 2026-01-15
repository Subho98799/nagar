import type { TimelineEvent } from "~/data/mock-issues";
import styles from "./confidence-timeline.module.css";

interface ConfidenceTimelineProps {
  /**
   * Timeline events to display
   * @important
   */
  events: TimelineEvent[];
  className?: string;
}

/**
 * Visual timeline showing how understanding of an issue evolved over time
 */
export function ConfidenceTimeline({ events, className }: ConfidenceTimelineProps) {
  return (
    <div className={`${styles.container} ${className || ""}`}>
      <div className={styles.header}>
        <h3 className={styles.title}>Understanding Timeline</h3>
        <p className={styles.subtitle}>How our understanding of this situation evolved based on citizen reports</p>
      </div>

      <div className={styles.timeline}>
        <div className={styles.line} />
        <div className={styles.events}>
          {events.map((event) => (
            <div key={event.id} className={styles.event}>
              <div className={`${styles.marker} ${styles[event.confidence.toLowerCase()]}`} />
              <div>
                <div className={styles.time}>{event.time}</div>
                <div className={styles.description}>{event.description}</div>
                <span className={`${styles.confidenceBadge} ${styles[event.confidence.toLowerCase()]}`}>
                  {event.confidence} Confidence
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
