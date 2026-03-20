import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Menu, X } from "lucide-react";

const navLinks = ["How It Works", "Benefits", "Community"];

const Navbar = () => {
  const [mobileOpen, setMobileOpen] = useState(false);
  const navigate = useNavigate();

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 nav-glass">
      <div className="w-full px-4 md:px-6 relative flex items-center h-[3.4rem]">
        {/* Logo + Site Name — top-left, clickable → home */}
        <button
          onClick={() => navigate("/")}
          className="flex items-center gap-2 shrink-0 cursor-pointer"
        >
          <div className="gold-dot" />
          <span className="font-semibold text-lg tracking-tight text-white">Mind Tutor</span>
        </button>

        {/* Nav links — absolutely centered in the panel */}
        <div className="nav-reduced hidden md:flex absolute left-1/2 -translate-x-1/2 items-center gap-1">
          {navLinks.map((link) => (
            <a
              key={link}
              href={`#${link.toLowerCase().replace(/\s+/g, "-")}`}
              className="px-4 py-2 text-sm font-medium text-white/70 hover:text-white transition-colors rounded-xl hover:bg-white/10"
            >
              {link}
            </a>
          ))}
        </div>

        {/* Spacer pushes right-side content to the edge */}
        <div className="flex-1" />

        {/* "Log in" + "Start Learning" — top-right */}
        <div className="nav-reduced hidden md:flex items-center gap-3">
          <Button variant="ghost" size="sm" className="text-white/80 hover:text-white hover:bg-white/10" onClick={() => navigate("/login")}>Log in</Button>
          <Button variant="hero" size="default" onClick={() => navigate("/start-learning")}>Start Learning</Button>
        </div>

        {/* Mobile hamburger */}
        <button
          onClick={() => setMobileOpen(!mobileOpen)}
          className="nav-reduced md:hidden p-2 rounded-xl hover:bg-secondary/60 transition-colors"
        >
          {mobileOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
        </button>
      </div>

      {mobileOpen && (
        <div className="md:hidden nav-glass px-4 pb-4 pt-2 space-y-1">
          {navLinks.map((link) => (
            <a
              key={link}
              href={`#${link.toLowerCase().replace(/\s+/g, "-")}`}
              className="block px-4 py-2.5 text-sm font-medium text-white/70 hover:text-white rounded-xl hover:bg-white/10 transition-colors"
              onClick={() => setMobileOpen(false)}
            >
              {link}
            </a>
          ))}
          <div className="pt-2 space-y-2">
            <Button variant="ghost" className="w-full text-white/80 hover:text-white hover:bg-white/10" onClick={() => navigate("/login")}>Log in</Button>
            <Button variant="hero" className="w-full" onClick={() => navigate("/start-learning")}>Start Learning</Button>
          </div>
        </div>
      )}
    </nav>
  );
};

export default Navbar;
