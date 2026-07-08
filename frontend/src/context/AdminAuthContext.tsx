"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";
import { useRouter } from "next/navigation";
import type { VerifyOTPResponse } from "@/lib/types";

const ADMIN_TOKEN_KEY = "ojabulk_admin_token";
const ADMIN_NAME_KEY = "ojabulk_admin_name";
const ADMIN_MARKET_KEY = "ojabulk_admin_market";

interface AdminSession {
  displayName: string;
  marketName: string | null;
}

interface AdminAuthContextValue {
  session: AdminSession | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (result: VerifyOTPResponse) => void;
  logout: () => void;
}

const AdminAuthContext = createContext<AdminAuthContextValue | undefined>(
  undefined
);

export function AdminAuthProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  const [session, setSession] = useState<AdminSession | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    const timeoutId = window.setTimeout(() => {
      const token = localStorage.getItem(ADMIN_TOKEN_KEY);
      const name = localStorage.getItem(ADMIN_NAME_KEY);
      if (token && name) {
        setSession({
          displayName: name,
          marketName: localStorage.getItem(ADMIN_MARKET_KEY),
        });
      }
      setIsLoading(false);
    }, 0);

    return () => window.clearTimeout(timeoutId);
  }, []);

  const login = useCallback(
    (result: VerifyOTPResponse) => {
      if (result.role !== "head_of_traders") {
        throw new Error(
          "This account doesn't have admin access. Log in with a head-of-traders account."
        );
      }
      localStorage.setItem(ADMIN_TOKEN_KEY, result.access_token);
      localStorage.setItem(ADMIN_NAME_KEY, result.display_name);
      if (result.market_name) {
        localStorage.setItem(ADMIN_MARKET_KEY, result.market_name);
      }
      setSession({
        displayName: result.display_name,
        marketName: result.market_name,
      });
      router.push("/admin/dashboard");
    },
    [router]
  );

  const logout = useCallback(() => {
    localStorage.removeItem(ADMIN_TOKEN_KEY);
    localStorage.removeItem(ADMIN_NAME_KEY);
    localStorage.removeItem(ADMIN_MARKET_KEY);
    setSession(null);
    router.push("/admin");
  }, [router]);

  return (
    <AdminAuthContext.Provider
      value={{
        session,
        isLoading,
        isAuthenticated: !!session,
        login,
        logout,
      }}
    >
      {children}
    </AdminAuthContext.Provider>
  );
}

export function useAdminAuth() {
  const ctx = useContext(AdminAuthContext);
  if (!ctx) throw new Error("useAdminAuth must be used within AdminAuthProvider");
  return ctx;
}

export function getAdminToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(ADMIN_TOKEN_KEY);
}