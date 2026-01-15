import { useState, useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router";
import { Header } from "~/components/header";
import { Button } from "~/components/ui/button/button";
import { Input } from "~/components/ui/input/input";
import { verifyOTP, sendOTP } from "~/lib/auth";
import styles from "./verify-otp.module.css";

export default function VerifyOTP() {
  const [searchParams] = useSearchParams();
  const phoneNumber = searchParams.get("phone") || "";
  const navigate = useNavigate();

  const [otp, setOtp] = useState("");
  const [loading, setLoading] = useState(false);
  const [resending, setResending] = useState(false);
  const [error, setError] = useState("");
  const [countdown, setCountdown] = useState(0);

  useEffect(() => {
    if (!phoneNumber) {
      navigate("/login");
    }
  }, [phoneNumber, navigate]);

  useEffect(() => {
    // Countdown timer for resend OTP
    if (countdown > 0) {
      const timer = setTimeout(() => setCountdown(countdown - 1), 1000);
      return () => clearTimeout(timer);
    }
  }, [countdown]);

  const handleVerifyOTP = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      if (otp.length !== 6) {
        setError("Please enter a 6-digit OTP");
        setLoading(false);
        return;
      }

      const result = await verifyOTP(phoneNumber, otp);
      
      if (result.success && result.user) {
        // Navigate to home page after successful authentication
        navigate("/");
      } else {
        setError(result.message || "Invalid OTP. Please try again.");
      }
    } catch (err: any) {
      setError(err.message || "Failed to verify OTP. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleResendOTP = async () => {
    setError("");
    setResending(true);

    try {
      const result = await sendOTP(phoneNumber);
      if (result.success) {
        setCountdown(60); // 60 second countdown
        setOtp(""); // Clear current OTP
      } else {
        setError(result.message || "Failed to resend OTP");
      }
    } catch (err: any) {
      setError(err.message || "Failed to resend OTP. Please try again.");
    } finally {
      setResending(false);
    }
  };

  const handleOtpChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value.replace(/\D/g, "").slice(0, 6);
    setOtp(value);
    setError("");
  };

  if (!phoneNumber) {
    return null;
  }

  return (
    <div className={styles.page}>
      <Header />
      <main className={styles.container}>
        <div className={styles.card}>
          <div className={styles.header}>
            <h1 className={styles.title}>Verify OTP</h1>
            <p className={styles.subtitle}>
              Enter the 6-digit OTP sent to <strong>{phoneNumber}</strong>
            </p>
          </div>

          <form onSubmit={handleVerifyOTP} className={styles.form}>
            <div className={styles.field}>
              <label className={styles.label} htmlFor="otp">
                OTP Code <span className={styles.required}>*</span>
              </label>
              <Input
                id="otp"
                type="text"
                inputMode="numeric"
                placeholder="123456"
                value={otp}
                onChange={handleOtpChange}
                required
                disabled={loading}
                className={styles.otpInput}
                maxLength={6}
                autoFocus
              />
              <span className={styles.helpText}>Enter the 6-digit code sent to your phone</span>
            </div>

            {error && (
              <div className={styles.error}>
                {error}
              </div>
            )}

            <Button type="submit" size="lg" disabled={loading || otp.length !== 6} className={styles.submitButton}>
              {loading ? "Verifying..." : "Verify OTP"}
            </Button>

            <div className={styles.resendSection}>
              <p className={styles.resendText}>Didn't receive the OTP?</p>
              <Button
                type="button"
                variant="outline"
                onClick={handleResendOTP}
                disabled={resending || countdown > 0}
                className={styles.resendButton}
              >
                {countdown > 0 ? `Resend OTP in ${countdown}s` : resending ? "Sending..." : "Resend OTP"}
              </Button>
            </div>

            <Button
              type="button"
              variant="ghost"
              onClick={() => navigate("/login")}
              className={styles.backButton}
            >
              Change Phone Number
            </Button>
          </form>
        </div>
      </main>
    </div>
  );
}
