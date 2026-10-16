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
    const code     = params.get("code");
    const token    = params.get("token");
    const userB64  = params.get("user");
    const error    = params.get("error");

    if (error) {
      const msg =
        error === "google_denied"     ? "Google sign-in was cancelled."
        : error === "facebook_denied" ? "Facebook sign-in was cancelled."
        : error === "no_email"        ? "Your account has no email address. Please use email/password sign-in."
        : "OAuth sign-in failed. Please try again.";
      navigate(`/login?oauthError=${encodeURIComponent(msg)}`, { replace: true });
      return;
    }

    if (code) {
      // Exchange single-use authorization code securely via POST request body
      fetch(`${import.meta.env.VITE_API_URL || ""}/api/auth/oauth/exchange`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ code }),
      })
        .then(async (res) => {
          if (!res.ok) {
            const errData = await res.json().catch(() => ({}));
            throw new Error(errData.detail || "Code exchange failed");
          }
          return res.json();
        })
        .then((data) => {
          login(data.access_token, data.user);
          navigate("/login-success", { replace: true });
        })
        .catch((err) => {
          navigate(`/login?oauthError=${encodeURIComponent(err.message || "OAuth exchange failed")}`, { replace: true });
        });
      return;
    }

    // Legacy fallback if token was provided in query parameters
    if (token && userB64) {
      try {
        const user: AuthUser = JSON.parse(atob(userB64.replace(/-/g, "+").replace(/_/g, "/")));
        login(token, user);
        navigate("/login-success", { replace: true });
      } catch {
        navigate("/login?oauthError=Invalid+response+from+server", { replace: true });
      }
      return;
    }

    navigate("/login?oauthError=Missing+OAuth+credentials", { replace: true });
  }, []);

  return (
    <div className="min-h-screen hero-arch flex items-center justify-center">
      <Loader2 className="w-8 h-8 animate-spin text-primary" />
    </div>
  );
};

export default OAuthCallbackPage;
