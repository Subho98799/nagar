import { Link, useLocation, useNavigate } from "react-router";
import { useState, useEffect } from "react";
<<<<<<< Updated upstream
import { Radio, FileText, Shield, MessageSquare, Map, User, LogOut, Clock } from "lucide-react";
=======
import { Radio, FileText, Shield, MessageSquare, Map, User, LogOut, Clock, Activity, Globe } from "lucide-react";
import { useTranslation } from "react-i18next";
>>>>>>> Stashed changes
import { getCurrentUser, logout, isAuthenticated } from "~/lib/auth";
import type { AuthUser } from "~/lib/auth";
import { Button } from "~/components/ui/button/button";
import styles from "./header.module.css";

export function Header() {
  const location = useLocation();
  const navigate = useNavigate();
  const { t, i18n } = useTranslation();
  const [user, setUser] = useState<AuthUser | null>(null);
  const [language, setLanguage] = useState(i18n.language || 'en');

  useEffect(() => {
    // Check authentication status
    if (isAuthenticated()) {
      setUser(getCurrentUser());
    } else {
      setUser(null);
    }
  }, [location.pathname]); // Re-check on route change

  const isActive = (path: string) => location.pathname === path;

  const handleLogout = () => {
    logout();
    setUser(null);
    navigate("/login");
  };

  const toggleLanguage = () => {
    const newLang = language === 'en' ? 'hi' : 'en';
    setLanguage(newLang);
    i18n.changeLanguage(newLang);
    localStorage.setItem('i18nextLng', newLang);
    document.documentElement.lang = newLang;
  };

  return (
    <header className={styles.header}>
      <div className={styles.container}>
        <Link to="/" className={styles.brand}>
          <Radio className={styles.logo} />
          <div className={styles.brandText}>
            <div className={styles.brandName}>{t('common.appName')}</div>
            <div className={styles.brandTagline}>{t('common.tagline')}</div>
          </div>
        </Link>

        <nav className={styles.nav}>
          <Link to="/" className={`${styles.navLink} ${isActive("/") ? styles.active : ""}`}>
            <Radio className={styles.navIcon} />
            <span>{t('common.dashboard')}</span>
          </Link>
<<<<<<< Updated upstream
=======
          <Link to="/city-overview" className={`${styles.navLink} ${isActive("/city-overview") ? styles.active : ""}`}>
            <Activity className={styles.navIcon} />
            <span>{t('common.cityPulse')}</span>
          </Link>
>>>>>>> Stashed changes
          <Link to="/map" className={`${styles.navLink} ${isActive("/map") ? styles.active : ""}`}>
            <Map className={styles.navIcon} />
            <span>{t('common.map')}</span>
          </Link>
          <Link to="/report" className={`${styles.navLink} ${isActive("/report") ? styles.active : ""}`}>
            <FileText className={styles.navIcon} />
            <span>{t('common.report')}</span>
          </Link>
          <Link to="/updates" className={`${styles.navLink} ${isActive("/updates") ? styles.active : ""}`}>
            <MessageSquare className={styles.navIcon} />
            <span>{t('common.updates')}</span>
          </Link>
          <Link to="/admin" className={`${styles.navLink} ${isActive("/admin") ? styles.active : ""}`}>
            <Shield className={styles.navIcon} />
            <span>{t('common.admin')}</span>
          </Link>
<<<<<<< Updated upstream
          <Link to="/timeline" className={`${styles.navLink} ${isActive("/timeline") ? styles.active : ""}`}>
            <Clock className={styles.navIcon} />
            <span>Timeline</span>
          </Link>
=======
          {ENABLE_TIMELINE && (
            <Link to="/timeline" className={`${styles.navLink} ${isActive("/timeline") ? styles.active : ""}`}>
              <Clock className={styles.navIcon} />
              <span>{t('common.timeline')}</span>
            </Link>
          )}
>>>>>>> Stashed changes
        </nav>

        <div className={styles.userSection}>
          <Button
            variant="ghost"
            size="sm"
            onClick={toggleLanguage}
            className={styles.languageButton}
            title={t('common.language')}
          >
            <Globe className={styles.languageIcon} />
            <span className={styles.languageText}>{language.toUpperCase()}</span>
          </Button>
          {user ? (
            <div className={styles.userInfo}>
              <User className={styles.userIcon} />
              <div className={styles.userDetails}>
                <span className={styles.userPhone}>{user.phone_number}</span>
                {user.name && <span className={styles.userName}>{user.name}</span>}
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={handleLogout}
                className={styles.logoutButton}
                title={t('common.logout')}
              >
                <LogOut className={styles.logoutIcon} />
                <span className={styles.logoutText}>{t('common.logout')}</span>
              </Button>
            </div>
          ) : (
            <Link to="/login" className={styles.loginLink}>
              <User className={styles.userIcon} />
              <span>{t('common.login')}</span>
            </Link>
          )}
        </div>
      </div>
    </header>
  );
}
