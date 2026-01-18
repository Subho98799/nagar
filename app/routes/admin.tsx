import { useState, useEffect } from "react";
import { Shield, MapPin, User } from "lucide-react";
import { Header } from "~/components/header";
import { Button } from "~/components/ui/button/button";
import { Textarea } from "~/components/ui/textarea/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "~/components/ui/select/select";
import { Badge } from "~/components/ui/badge/badge";
import { mockIssues } from "~/data/mock-issues";
import { USE_MOCK } from "~/lib/config";
import { fetchIssues } from "~/lib/api";
import type { Issue, Confidence, Status } from "~/data/mock-issues";
import { toast } from "~/hooks/use-toast";
import { useLanguage } from "~/context/LanguageContext";
import { t } from "~/lib/i18n";
import styles from "./admin.module.css";

const severityVariant = {
  Low: "secondary" as const,
  Medium: "default" as const,
  High: "destructive" as const,
};

export default function Admin() {
  const { lang } = useLanguage();
  const [issues, setIssues] = useState<Issue[]>(mockIssues);

  useEffect(() => {
    let mounted = true;
    if (USE_MOCK) {
      if (mounted) setIssues(mockIssues);
      return () => {
        mounted = false;
      };
    }

    fetchIssues()
      .then((serverIssues) => {
        const mapped = serverIssues.map((s) => ({
          id: s.id,
          type: ((): any => {
            const it = s.issue_type || "";
            if (/traffic|road/i.test(it)) return "Traffic";
            if (/power|electric/i.test(it)) return "Power";
            if (/water/i.test(it)) return "Water";
            if (/infrastructure|roadblock|bridge/i.test(it)) return "Roadblock";
            if (/safety|crime|security/i.test(it)) return "Safety";
            return "Other";
          })(),
          title: s.title,
          location: s.locality ? `${s.locality}, ${s.city || ""}`.trim().replace(/, $/, "") : s.city || "",
          description: s.description,
          severity: (s.severity || "Low") as any,
          confidence: (s.confidence === "HIGH" ? "High" : s.confidence === "MEDIUM" ? "Medium" : "Low") as any,
          status: s.status === "CONFIRMED" || s.status === "ACTIVE" ? "Active" : s.status === "RESOLVED" ? "Resolved" : "Under Review",
          timestamp: s.created_at || new Date().toISOString(),
          reportCount: s.report_count || 1,
          timeline: [
            {
              id: `${s.id}-t1`,
              timestamp: s.created_at || new Date().toISOString(),
              time: new Date(s.created_at || new Date().toISOString()).toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" }),
              confidence: (s.confidence === "HIGH" ? "High" : s.confidence === "MEDIUM" ? "Medium" : "Low") as any,
              description: s.description || "",
            },
          ],
          operatorNotes: s.operatorNotes,
        }));
        if (mounted) setIssues(mapped as any);
      })
      .catch((err) => {
        // Do not fallback to mock automatically. Log and show empty list.
        // eslint-disable-next-line no-console
        console.error("fetchIssues failed:", err);
        if (mounted) setIssues([]);
      });

    return () => {
      mounted = false;
    };
  }, []);

  const handleConfidenceChange = (issueId: string, confidence: Confidence) => {
    setIssues((prev) => prev.map((issue) => (issue.id === issueId ? { ...issue, confidence } : issue)));
  };

  const handleStatusChange = (issueId: string, status: Status) => {
    setIssues((prev) => prev.map((issue) => (issue.id === issueId ? { ...issue, status } : issue)));
  };

  const handleNotesChange = (issueId: string, notes: string) => {
    setIssues((prev) => prev.map((issue) => (issue.id === issueId ? { ...issue, operatorNotes: notes } : issue)));
  };

  const handleSave = (issueId: string) => {
    toast({
      title: t(lang, "changes_saved"),
      description: t(lang, "issue_updated"),
    });
  };

  return (
    <div className={styles.page}>
      <Header />
      <main className={styles.container}>
        <div className={styles.header}>
          <h1 className={styles.title}>
            <Shield className={styles.titleIcon} />
            {t(lang, "operator_console")}
          </h1>
          <p className={styles.subtitle}>{t(lang, "human_oversight")}</p>
          <div className={styles.badge}>
            <User className={styles.badgeIcon} />
            {t(lang, "human_oversight_active")}
          </div>
        </div>

        <div className={styles.issuesList}>
          {issues.map((issue) => (
            <div key={issue.id} className={styles.issueCard}>
              <div className={styles.issueHeader}>
                <div>
                  <h3 className={styles.issueTitle}>{issue.title}</h3>
                  <div className={styles.issueLocation}>
                    <MapPin className={styles.locationIcon} />
                    <span>{issue.location}</span>
                  </div>
                </div>
                <Badge variant={severityVariant[issue.severity]}>{issue.severity}</Badge>
              </div>

              <div className={styles.controls}>
                <div className={styles.controlGroup}>
                  <label className={styles.controlLabel}>{t(lang, "confidence_level")}</label>
                  <Select
                    value={issue.confidence}
                    onValueChange={(value) => handleConfidenceChange(issue.id, value as Confidence)}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="Low">{t(lang, "confidence_low")}</SelectItem>
                      <SelectItem value="Medium">{t(lang, "confidence_medium")}</SelectItem>
                      <SelectItem value="High">{t(lang, "confidence_high")}</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className={styles.controlGroup}>
                  <label className={styles.controlLabel}>{t(lang, "status_label")}</label>
                  <Select value={issue.status} onValueChange={(value) => handleStatusChange(issue.id, value as Status)}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="Under Review">{t(lang, "under_review")}</SelectItem>
                      <SelectItem value="Active">{t(lang, "active")}</SelectItem>
                      <SelectItem value="Resolved">{t(lang, "resolved")}</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div className={styles.notesSection}>
                <label className={styles.notesLabel}>{t(lang, "internal_notes")}</label>
                <Textarea
                  placeholder={t(lang, "notes_placeholder")}
                  rows={3}
                  value={issue.operatorNotes || ""}
                  onChange={(e) => handleNotesChange(issue.id, e.target.value)}
                />
                <Button className={styles.saveButton} onClick={() => handleSave(issue.id)}>
                  {t(lang, "save_changes")}
                </Button>
              </div>
            </div>
          ))}
        </div>
      </main>
    </div>
  );
}
