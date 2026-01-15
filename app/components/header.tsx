import { Link, useLocation, useNavigate } from "react-router";
import { useState, useEffect } from "react";
import { Radio, FileText, Shield, MessageSquare, Map, User, LogOut, Clock } from "lucide-react";
import { getCurrentUser, logout, isAuthenticated } from "~/lib/auth";
import type { AuthUser } from "~/lib/auth";
import { Button } from "~/components/ui/button/button";
import styles from "./header.module.css";

export function Header() {
  const location = useLocation();
  const navigate = useNavigate();
  const [user, setUser] = useState<AuthUser | null>(null);

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
            <div className={styles.brandName}>Nagar Alert Hub</div>
            <div className={styles.brandTagline}>Civic Intelligence Platform</div>
          </div>
        </Link>

        <nav className={styles.nav}>
          <Link to="/" className={`${styles.navLink} ${isActive("/") ? styles.active : ""}`}>
            <Radio className={styles.navIcon} />
            <span>Dashboard</span>
          </Link>
          <Link to="/map" className={`${styles.navLink} ${isActive("/map") ? styles.active : ""}`}>
            <Map className={styles.navIcon} />
            <span>Map</span>
          </Link>
          <Link to="/report" className={`${styles.navLink} ${isActive("/report") ? styles.active : ""}`}>
            <FileText className={styles.navIcon} />
            <span>Report</span>
          </Link>
          <Link to="/updates" className={`${styles.navLink} ${isActive("/updates") ? styles.active : ""}`}>
            <MessageSquare className={styles.navIcon} />
            <span>Updates</span>
          </Link>
          <Link to="/admin" className={`${styles.navLink} ${isActive("/admin") ? styles.active : ""}`}>
            <Shield className={styles.navIcon} />
            <span>Admin</span>
          </Link>
          <Link to="/timeline" className={`${styles.navLink} ${isActive("/timeline") ? styles.active : ""}`}>
            <Clock className={styles.navIcon} />
            <span>Timeline</span>
          </Link>
        </nav>

        <div className={styles.userSection}>
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
                title="Logout"
              >
                <LogOut className={styles.logoutIcon} />
                <span className={styles.logoutText}>Logout</span>
              </Button>
            </div>
          ) : (
            <Link to="/login" className={styles.loginLink}>
              <User className={styles.userIcon} />
              <span>Login</span>
            </Link>
          )}
        </div>
      </div>
    </header>
  );
}
