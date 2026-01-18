import { Link, useLocation, useNavigate } from "react-router";
import { useState, useEffect } from "react";
import { Radio, FileText, Shield, MessageSquare, Map, User, LogOut, Clock, Activity } from "lucide-react";
import { getCurrentUser, logout, isAuthenticated } from "~/lib/auth";
import type { AuthUser } from "~/lib/auth";
import { Button } from "~/components/ui/button/button";
import { ENABLE_TIMELINE } from "~/lib/config";
import { useLanguage } from "~/context/LanguageContext";
import { t } from "~/lib/i18n";
import styles from "./header.module.css";

export function Header() {
  const location = useLocation();
  const navigate = useNavigate();
  const [user, setUser] = useState<AuthUser | null>(null);
  const { lang, toggle } = useLanguage();

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

  return (
    <header className={styles.header}>
      <div className={styles.container}>
        <Link to="/" className={styles.brand}>
          <Radio className={styles.logo} />
          <div className={styles.brandText}>
            <div className={styles.brandName}>{t(lang, "app_name")}</div>
            <div className={styles.brandTagline}>{t(lang, "app_tagline")}</div>
          </div>
        </Link>

        <nav className={styles.nav}>
          <Link to="/" className={`${styles.navLink} ${isActive("/") ? styles.active : ""}`}>
            <Radio className={styles.navIcon} />
            <span>{t(lang, "dashboard")}</span>
          </Link>
          <Link to="/city-overview" className={`${styles.navLink} ${isActive("/city-overview") ? styles.active : ""}`}>
            <Activity className={styles.navIcon} />
            <span>{t(lang, "city_pulse")}</span>
          </Link>
          <Link to="/map" className={`${styles.navLink} ${isActive("/map") ? styles.active : ""}`}>
            <Map className={styles.navIcon} />
            <span>{t(lang, "map")}</span>
          </Link>
          <Link to="/report" className={`${styles.navLink} ${isActive("/report") ? styles.active : ""}`}>
            <FileText className={styles.navIcon} />
            <span>{t(lang, "report")}</span>
          </Link>
          <Link to="/updates" className={`${styles.navLink} ${isActive("/updates") ? styles.active : ""}`}>
            <MessageSquare className={styles.navIcon} />
            <span>{t(lang, "updates")}</span>
          </Link>
          <Link to="/admin" className={`${styles.navLink} ${isActive("/admin") ? styles.active : ""}`}>
            <Shield className={styles.navIcon} />
            <span>{t(lang, "admin")}</span>
          </Link>
          {ENABLE_TIMELINE && (
            <Link to="/timeline" className={`${styles.navLink} ${isActive("/timeline") ? styles.active : ""}`}>
              <Clock className={styles.navIcon} />
              <span>{t(lang, "timeline")}</span>
            </Link>
          )}
        </nav>

        <div className={styles.userSection}>
          <button
            onClick={toggle}
            style={{
              padding: "8px 12px",
              marginRight: "12px",
              border: "1px solid #e5e7eb",
              borderRadius: "6px",
              background: "white",
              cursor: "pointer",
              fontSize: "14px",
              fontWeight: "500",
            }}
          >
            {lang === "en" ? t(lang, "switch_to_hindi") : t(lang, "switch_to_english")}
          </button>
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
                title={t(lang, "logout")}
              >
                <LogOut className={styles.logoutIcon} />
                <span className={styles.logoutText}>{t(lang, "logout")}</span>
              </Button>
            </div>
          ) : (
            <Link to="/login" className={styles.loginLink}>
              <User className={styles.userIcon} />
              <span>{t(lang, "login")}</span>
            </Link>
          )}
        </div>
      </div>
    </header>
  );
}
