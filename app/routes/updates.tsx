import { MessageSquare } from "lucide-react";
import { Header } from "~/components/header";
import { useLanguage } from "~/context/LanguageContext";
import { t } from "~/lib/i18n";
import styles from "./updates.module.css";

export default function Updates() {
  const { lang } = useLanguage();
  return (
    <div className={styles.page}>
      <Header />
      <main className={styles.container}>
        <div className={styles.header}>
          <h1 className={styles.title}>{t(lang, "curated_updates")}</h1>
          <p className={styles.subtitle}>{t(lang, "updates_subtitle")}</p>
        </div>

        <div className={styles.previewCard}>
          <div className={styles.previewHeader}>
            <MessageSquare className={styles.whatsappIcon} />
            <h2 className={styles.previewTitle}>{t(lang, "whatsapp_preview")}</h2>
          </div>

          <div className={styles.messages}>
            <div className={styles.message}>
              <div className={styles.messageHeader}>
                <span className={styles.messageSender}>{t(lang, "whatsapp_sender")}</span>
                <span className={styles.messageTime}>10:30 AM</span>
              </div>
              <p className={styles.messageText}>
                🚦 <strong>{t(lang, "traffic_update")}</strong>
                <br />
                <br />
                {t(lang, "traffic_congestion_reported")}
                <br />
                <br />
                {t(lang, "based_on_reports").replace("{count}", "12").replace("{time}", "11:30 AM")}
              </p>
            </div>

            <div className={styles.message}>
              <div className={styles.messageHeader}>
                <span className={styles.messageSender}>{t(lang, "whatsapp_sender")}</span>
                <span className={styles.messageTime}>9:45 AM</span>
              </div>
              <p className={styles.messageText}>
                ⚡ <strong>{t(lang, "power_update")}</strong>
                <br />
                <br />
                {t(lang, "power_outage_affecting")}
                <br />
                <br />
                {t(lang, "will_keep_informed")}
              </p>
            </div>

            <div className={styles.message}>
              <div className={styles.messageHeader}>
                <span className={styles.messageSender}>{t(lang, "whatsapp_sender")}</span>
                <span className={styles.messageTime}>{t(lang, "yesterday")}</span>
              </div>
              <p className={styles.messageText}>
                ✅ <strong>{t(lang, "resolved")}</strong>
                <br />
                <br />
                {t(lang, "railway_crossing_cleared")}
                <br />
                <br />
                {t(lang, "thank_you_patience")}
              </p>
            </div>
          </div>
        </div>

        <div className={styles.infoCard}>
          <h3 className={styles.infoTitle}>{t(lang, "communication_principles")}</h3>
          <ul className={styles.infoList}>
            <li>{t(lang, "principle_1")}</li>
            <li>{t(lang, "principle_2")}</li>
            <li>{t(lang, "principle_3")}</li>
            <li>{t(lang, "principle_4")}</li>
            <li>{t(lang, "principle_5")}</li>
            <li>{t(lang, "principle_6")}</li>
          </ul>
        </div>
      </main>
    </div>
  );
}
