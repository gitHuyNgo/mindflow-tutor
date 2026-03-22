import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
import { AuthProvider } from "@/contexts/AuthContext";
import Index from "./pages/Index.tsx";
import StartLearning from "./pages/StartLearning.tsx";
import Login from "./pages/Login.tsx";
import VerifyEmail from "./pages/VerifyEmail.tsx";
import LoginSuccess from "./pages/LoginSuccess.tsx";
import OAuthCallback from "./pages/OAuthCallback.tsx";
import NotFound from "./pages/NotFound.tsx";
import Session from "./pages/Session.tsx";
import Dashboard from "./pages/Dashboard.tsx";
import SessionUser from "./pages/SessionUser.tsx";

const queryClient = new QueryClient();

const App = () => (
  <QueryClientProvider client={queryClient}>
    <AuthProvider>
      <TooltipProvider>
        <Toaster />
        <Sonner />
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<Index />} />
            <Route path="/start-learning" element={<StartLearning />} />
            <Route path="/login" element={<Login />} />
            <Route path="/login-success" element={<LoginSuccess />} />
            <Route path="/verify-email" element={<VerifyEmail />} />
            <Route path="/oauth-callback" element={<OAuthCallback />} />
            <Route path="/session" element={<Session />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/session-user" element={<SessionUser />} />
            {/* ADD ALL CUSTOM ROUTES ABOVE THE CATCH-ALL "*" ROUTE */}
            <Route path="*" element={<NotFound />} />
          </Routes>
        </BrowserRouter>
      </TooltipProvider>
    </AuthProvider>
  </QueryClientProvider>
);

export default App;
