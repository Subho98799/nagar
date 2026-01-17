import { MessageSquare } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Header } from "~/components/header";
import styles from "./updates.module.css";

export default function Updates() {
  const { t } = useTranslation();
  
  return (
    <div className={styles.page}>
      <Header />
      <main className={styles.container}>
        <div className={styles.header}>
          <h1 className={styles.title}>{t('updates.title')}</h1>
          <p className={styles.subtitle}>
            {t('whatsapp.preview')}
          </p>
        </div>

        <div className={styles.previewCard}>
          <div className={styles.previewHeader}>
            <MessageSquare className={styles.whatsappIcon} />
            <h2 className={styles.previewTitle}>{t('whatsapp.preview')}</h2>
          </div>

          <div className={styles.messages}>
            <div className={styles.message}>
              <div className={styles.messageHeader}>
                <span className={styles.messageSender}>{t('common.appName')}</span>
                <span className={styles.messageTime}>10:30 AM</span>
              </div>
              <p className={styles.messageText}>
                🚦 <strong>{t('whatsapp.trafficUpdate')}</strong>
                <br />
                <br />
                {t('updates.trafficMsg1')}
                <br />
                <br />
                {t('updates.basedOn')}
              </p>
            </div>

            <div className={styles.message}>
              <div className={styles.messageHeader}>
                <span className={styles.messageSender}>{t('common.appName')}</span>
                <span className={styles.messageTime}>9:45 AM</span>
              </div>
              <p className={styles.messageText}>
                ⚡ <strong>{t('whatsapp.powerUpdate')}</strong>
                <br />
                <br />
                {t('updates.powerMsg1')}
                <br />
                <br />
                {t('updates.weWillKeepYou')}
              </p>
            </div>

            <div className={styles.message}>
              <div className={styles.messageHeader}>
                <span className={styles.messageSender}>Nagar Alert Hub</span>
                <span className={styles.messageTime}>{t('updates.yesterday')}</span>
              </div>
              <p className={styles.messageText}>
                ✅ <strong>{t('common.success')}</strong>
                <br />
                <br />
                {t('updates.resolvedMsg')}
                <br />
                <br />
                {t('updates.thankYou')}
              </p>
            </div>
          </div>
        </div>

        <div className={styles.infoCard}>
          <h3 className={styles.infoTitle}>{t('updates.principles')}</h3>
          <ul className={styles.infoList}>
            <li>{t('updates.principle1')}</li>
            <li>{t('updates.principle2')}</li>
            <li>{t('updates.principle3')}</li>
            <li>{t('updates.principle4')}</li>
            <li>{t('updates.principle5')}</li>
            <li>{t('updates.principle6')}</li>
          </ul>
        </div>
      </main>
    </div>
  );
}
