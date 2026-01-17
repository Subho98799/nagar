import { useMemo } from "react";
import { useTranslation } from "react-i18next";
import styles from "./city-pulse.module.css";
import { Activity } from "lucide-react";
import type { Issue } from "~/data/mock-issues";

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
  const { t } = useTranslation();
  
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
    let title = t("cityPulse.cityOperatingNormally");
    let description = t("cityPulse.noDisruptionsReported");
    let colorClass = styles.calm;

    if (count === 0) {
      // Calm state (default)
    } else if (count <= 2 && highSeverity === 0) {
      state = "moderate";
      title = t("cityPulse.minorDisruptionsTitle");
      description = t("cityPulse.minorDisruptionsDesc", {
        count: count,
        countText: t(count === 1 ? "cityPulse.issueHas" : "cityPulse.issuesHave"),
        reportText: mediumConfidence > 0 ? t("cityPulse.reportsBeingObserved") : t("cityPulse.situationsLocalized")
      });
      colorClass = styles.moderate;
    } else if (count <= 4 || highSeverity <= 1) {
      state = "moderate";
      title = t("cityPulse.moderateDisruptionsTitle");
      description = t("cityPulse.moderateDisruptionsDesc", {
        attentionText: highSeverity > 0
          ? t("cityPulse.someRequireAttention")
          : t("cityPulse.mostAppearManageable")
      });
      colorClass = styles.moderate;
    } else {
      state = "disrupted";
      title = t("cityPulse.multipleOngoingTitle");
      description = t("cityPulse.multipleOngoingDesc");
      colorClass = styles.disrupted;
    }

    return { state, title, description, colorClass };
  }, [issues, t]);

  return (
    <div className={`${styles.container} ${pulseData.colorClass} ${className || ""}`}>
      <div className={styles.header}>
        <div className={styles.iconWrapper}>
          <Activity className={styles.icon} aria-hidden="true" />
        </div>
        <div className={styles.content}>
          <h2 className={styles.label}>{t("cityPulse.pulseHeader")}</h2>
          <h3 className={styles.title}>{pulseData.title}</h3>
          <p className={styles.description}>{pulseData.description}</p>
        </div>
      </div>
      <div className={styles.indicator} aria-label={`City state: ${pulseData.state}`} />
    </div>
  );
}
