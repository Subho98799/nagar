import { useTranslation } from "react-i18next";
import styles from "./footer.module.css";

export function Footer() {
  const { t } = useTranslation();
  
  return (
    <footer className={styles.footer}>
      <p className={styles.text}>© 2026 {t('common.appName')} - Designed and Developed by The Shadow Syndicates</p>
    </footer>
  );
}
