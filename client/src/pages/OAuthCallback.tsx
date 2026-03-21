import { useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { Loader2 } from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";
import type { AuthUser } from "@/lib/auth";

const OAuthCallbackPage = () => {
  const navigate         = useNavigate();
  const [params]         = useSearchParams();
  const { login }        = useAuth();

  useEffect(() => {
    const token    = params.get("token");
    const userB64  = params.get("user");
    const error    = params.get("error");

    if (error || !token || !userB64) {
      const msg =
        error === "google_denied"   ? "Google sign-in was cancelled."
        : error === "facebook_denied" ? "Facebook sign-in was cancelled."
        : error === "no_email"        ? "Your account has no email address. Please use email/password sign-in."
        : "OAuth sign-in failed. Please try again.";
      navigate(`/login?oauthError=${encodeURIComponent(msg)}`, { replace: true });
      return;
    }

    try {
      const user: AuthUser = JSON.parse(atob(userB64.replace(/-/g, "+").replace(/_/g, "/")));
      login(token, user);
      navigate("/login-success", { replace: true });
    } catch {
      navigate("/login?oauthError=Invalid+response+from+server", { replace: true });
    }
  }, []);

  return (
    <div className="min-h-screen hero-arch flex items-center justify-center">
      <Loader2 className="w-8 h-8 animate-spin text-primary" />
    </div>
  );
};

export default OAuthCallbackPage;
