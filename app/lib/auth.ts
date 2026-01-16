/**
 * Authentication utilities and API functions.
 */

import { API_BASE_URL, ADMIN_PHONE_ALLOWLIST } from "./config";

export interface AuthUser {
  id: string;
  phone_number: string;
  name?: string;
  is_verified: boolean;
  created_at: string;
  last_login_at?: string;
}

export interface AuthResponse {
  success: boolean;
  message: string;
  user?: AuthUser;
  token?: string;
}

export interface OTPResponse {
  success: boolean;
  message: string;
  otp?: string; // Only in development - remove in production
  expires_in_minutes?: number;
}

/**
 * Send OTP to phone number.
 */
export async function sendOTP(phoneNumber: string): Promise<OTPResponse> {
  try {
    const response = await fetch(`${API_BASE_URL}/auth/send-otp`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ phone_number: phoneNumber }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || "Failed to send OTP");
    }

    return await response.json();
  } catch (error) {
    console.error("sendOTP error:", error);
    throw error;
  }
}

/**
 * Verify OTP and authenticate user.
 */
export async function verifyOTP(phoneNumber: string, otp: string): Promise<AuthResponse> {
  try {
    const response = await fetch(`${API_BASE_URL}/auth/verify-otp`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ phone_number: phoneNumber, otp }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || "Failed to verify OTP");
    }

    const data = await response.json();
    
    // Store auth token and user in localStorage
    if (data.token && data.user) {
      localStorage.setItem("auth_token", data.token);
      localStorage.setItem("auth_user", JSON.stringify(data.user));
    }

    return data;
  } catch (error) {
    console.error("verifyOTP error:", error);
    throw error;
  }
}

/**
 * Get current authenticated user from localStorage.
 */
export function getCurrentUser(): AuthUser | null {
  try {
    const userStr = localStorage.getItem("auth_user");
    if (!userStr) return null;
    return JSON.parse(userStr) as AuthUser;
  } catch {
    return null;
  }
}

/**
 * Get auth token from localStorage.
 */
export function getAuthToken(): string | null {
  return localStorage.getItem("auth_token");
}

/**
 * Check if user is authenticated.
 */
export function isAuthenticated(): boolean {
  return getCurrentUser() !== null && getAuthToken() !== null;
}

/**
 * Logout user (clear localStorage).
 */
export function logout(): void {
  localStorage.removeItem("auth_token");
  localStorage.removeItem("auth_user");
}

/**
 * Admin check (frontend-only guard).
 * This is NOT security; it's a demo/judging guardrail to keep analytics/admin-only surfaces out of the citizen UX.
 */
export function isAdminUser(): boolean {
  try {
    const user = getCurrentUser();
    if (!user?.phone_number) return false;
    const normalized = String(user.phone_number).replace(/\D/g, "");
    return Array.isArray(ADMIN_PHONE_ALLOWLIST) && ADMIN_PHONE_ALLOWLIST.includes(normalized);
  } catch {
    return false;
  }
}
