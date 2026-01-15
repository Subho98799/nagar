import { useState } from "react";
import { useNavigate } from "react-router";
import { Header } from "~/components/header";
import { Button } from "~/components/ui/button/button";
import { Input } from "~/components/ui/input/input";
import { sendOTP } from "~/lib/auth";
import styles from "./login.module.css";

export default function Login() {
  const [phoneNumber, setPhoneNumber] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [otpSent, setOtpSent] = useState(false);
  const navigate = useNavigate();

  const handleSendOTP = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      // Basic phone validation
      const normalized = phoneNumber.replace(/\D/g, "");
      if (normalized.length < 10) {
        setError("Please enter a valid phone number");
        setLoading(false);
        return;
      }

      const result = await sendOTP(phoneNumber);
      
      if (result.success) {
        setOtpSent(true);
        // Navigate to OTP verification page with phone number
        navigate(`/verify-otp?phone=${encodeURIComponent(phoneNumber)}`);
      } else {
        setError(result.message || "Failed to send OTP");
      }
    } catch (err: any) {
      setError(err.message || "Failed to send OTP. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={styles.page}>
      <Header />
      <main className={styles.container}>
        <div className={styles.card}>
          <div className={styles.header}>
            <h1 className={styles.title}>Login with Phone</h1>
            <p className={styles.subtitle}>Enter your phone number to receive an OTP</p>
          </div>

          <form onSubmit={handleSendOTP} className={styles.form}>
            <div className={styles.field}>
              <label className={styles.label} htmlFor="phone">
                Phone Number <span className={styles.required}>*</span>
              </label>
              <Input
                id="phone"
                type="tel"
                placeholder="+91 9876543210"
                value={phoneNumber}
                onChange={(e) => setPhoneNumber(e.target.value)}
                required
                disabled={loading}
                className={styles.input}
              />
              <span className={styles.helpText}>Include country code (e.g., +91 for India)</span>
            </div>

            {error && (
              <div className={styles.error}>
                {error}
              </div>
            )}

            <Button type="submit" size="lg" disabled={loading} className={styles.submitButton}>
              {loading ? "Sending OTP..." : "Send OTP"}
            </Button>
          </form>
        </div>
      </main>
    </div>
  );
}
