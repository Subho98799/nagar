import { MessageSquare } from "lucide-react";
import { Header } from "~/components/header";
import styles from "./updates.module.css";

export default function Updates() {
  return (
    <div className={styles.page}>
      <Header />
      <main className={styles.container}>
        <div className={styles.header}>
          <h1 className={styles.title}>Curated Updates</h1>
          <p className={styles.subtitle}>
            Preview of how calm, responsible updates would be shared with citizens via WhatsApp
          </p>
        </div>

        <div className={styles.previewCard}>
          <div className={styles.previewHeader}>
            <MessageSquare className={styles.whatsappIcon} />
            <h2 className={styles.previewTitle}>WhatsApp Message Preview</h2>
          </div>

          <div className={styles.messages}>
            <div className={styles.message}>
              <div className={styles.messageHeader}>
                <span className={styles.messageSender}>Nagar Alert Hub</span>
                <span className={styles.messageTime}>10:30 AM</span>
              </div>
              <p className={styles.messageText}>
                🚦 <strong>Traffic Update</strong>
                <br />
                <br />
                Traffic congestion reported near Main Chowk, Station Road. Consider using alternate routes if traveling
                in that area.
                <br />
                <br />
                Based on 12 citizen reports. Last updated: 11:30 AM
              </p>
            </div>

            <div className={styles.message}>
              <div className={styles.messageHeader}>
                <span className={styles.messageSender}>Nagar Alert Hub</span>
                <span className={styles.messageTime}>9:45 AM</span>
              </div>
              <p className={styles.messageText}>
                ⚡ <strong>Power Update</strong>
                <br />
                <br />
                Power outage affecting Sector 7 residential area. Approximately 200 households impacted. Restoration
                work is underway.
                <br />
                <br />
                We'll keep you informed as the situation develops.
              </p>
            </div>

            <div className={styles.message}>
              <div className={styles.messageHeader}>
                <span className={styles.messageSender}>Nagar Alert Hub</span>
                <span className={styles.messageTime}>Yesterday</span>
              </div>
              <p className={styles.messageText}>
                ✅ <strong>Resolved</strong>
                <br />
                <br />
                Railway Crossing road closure has been cleared. Traffic is flowing normally on NH-44.
                <br />
                <br />
                Thank you for your patience.
              </p>
            </div>
          </div>
        </div>

        <div className={styles.infoCard}>
          <h3 className={styles.infoTitle}>Communication Principles</h3>
          <ul className={styles.infoList}>
            <li>Calm, measured language without alarmist phrasing</li>
            <li>Clear indication of information source (citizen reports)</li>
            <li>Transparent about confidence levels and uncertainty</li>
            <li>Actionable guidance when appropriate</li>
            <li>Regular updates as situations evolve</li>
            <li>Positive confirmation when issues are resolved</li>
          </ul>
        </div>
      </main>
    </div>
  );
}
