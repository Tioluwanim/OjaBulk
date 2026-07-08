"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";
import { useRouter } from "next/navigation";
import {
  clearStoredToken,
  getStoredToken,
  setStoredToken,
} from "@/lib/api-client";
import { getMyProfile } from "@/lib/api/traders";
import type { TraderResponse, VerifyOTPResponse } from "@/lib/types";

interface AuthContextValue {
  trader: TraderResponse | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (result: VerifyOTPResponse) => Promise<void>;
  logout: () => void;
  refreshProfile: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [trader, setTrader] = useState<TraderResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();

  const loadProfile = useCallback(async () => {
    try {
      const profile = await getMyProfile();
      setTrader(profile);
    } catch {
      clearStoredToken();
      setTrader(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    const timeoutId = window.setTimeout(() => {
      const token = getStoredToken();
      if (token) {
        void loadProfile();
      } else {
        setIsLoading(false);
      }
    }, 0);

    return () => window.clearTimeout(timeoutId);
  }, [loadProfile]);

  const login = useCallback(
    async (result: VerifyOTPResponse) => {
      setStoredToken(result.access_token);
      setIsLoading(true);
      await loadProfile();
      router.push("/portal/home");
    },
    [loadProfile, router]
  );

  const logout = useCallback(() => {
    clearStoredToken();
    setTrader(null);
    router.push("/portal");
  }, [router]);

  return (
    <AuthContext.Provider
      value={{
        trader,
        isLoading,
        isAuthenticated: !!trader,
        login,
        logout,
        refreshProfile: loadProfile,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}