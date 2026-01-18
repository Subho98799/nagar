import { useMemo } from "react";
import styles from "./city-pulse.module.css";
import { Activity } from "lucide-react";
import type { Issue } from "~/data/mock-issues";
import { useLanguage } from "~/context/LanguageContext";
import { t } from "~/lib/i18n";

interface CityPulseProps {
  issues: Issue[];
  className?: string;
}

type CityState = "calm" | "moderate" | "disrupted";

interface PulseData {
  state: CityState;
  title: string;
  description: string;
  colorClass: string;
}

export function CityPulse({ issues, className }: CityPulseProps) {
  const { lang } = useLanguage();
  const pulseData: PulseData = useMemo(() => {
    const activeIssues = issues.filter((issue) => issue.status === "Active");
    const count = activeIssues.length;

    // Count severity distribution
    const highSeverity = activeIssues.filter((i) => i.severity === "High").length;
    const mediumSeverity = activeIssues.filter((i) => i.severity === "Medium").length;

    // Count confidence levels
    const highConfidence = activeIssues.filter((i) => i.confidence === "High").length;
    const mediumConfidence = activeIssues.filter((i) => i.confidence === "Medium").length;

    // Determine city state
    let state: CityState = "calm";
    let title = t(lang, "city_operating_normally");
    let description = t(lang, "city_stable");
    let colorClass = styles.calm;

    if (count === 0) {
      // Calm state (default)
    } else if (count <= 2 && highSeverity === 0) {
      state = "moderate";
      title = "Minor Disruptions Observed";
      description = `${count} ${count === 1 ? "issue has" : "issues have"} been reported in the city. ${
        mediumConfidence > 0 ? "Reports are being observed." : "Situations appear localized."
      } Most areas remain unaffected.`;
      colorClass = styles.moderate;
    } else if (count <= 4 || highSeverity <= 1) {
      state = "moderate";
      title = "Moderate Disruptions Reported";
      description = `Multiple incidents have been reported across different areas. ${
        highSeverity > 0
          ? "Some situations require attention."
          : "Most disruptions appear manageable."
      } Residents should stay informed.`;
      colorClass = styles.moderate;
    } else {
      state = "disrupted";
      title = "Multiple Ongoing Disruptions";
      description = "Multiple traffic and infrastructure-related issues have been reported across central areas. Daily commuters appear most affected. Situations are under observation.";
      colorClass = styles.disrupted;
    }

    return { state, title, description, colorClass };
  }, [issues]);

  return (
    <div className={`${styles.container} ${pulseData.colorClass} ${className || ""}`}>
      <div className={styles.header}>
        <div className={styles.iconWrapper}>
          <Activity className={styles.icon} aria-hidden="true" />
        </div>
        <div className={styles.content}>
          <h2 className={styles.label}>{t(lang, "city_pulse")}</h2>
          <h3 className={styles.title}>{pulseData.title}</h3>
          <p className={styles.description}>{pulseData.description}</p>
        </div>
      </div>
      <div className={styles.indicator} aria-label={`City state: ${pulseData.state}`} />
    </div>
  );
}
