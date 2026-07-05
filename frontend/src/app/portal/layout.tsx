import { AuthProvider } from "@/context/AuthContext";

export default function PortalLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <AuthProvider>{children}</AuthProvider>;
}