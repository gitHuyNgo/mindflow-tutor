import { useNavigate } from "react-router-dom";
import Navbar from "@/components/Navbar";
import HeroSection from "@/components/HeroSection";
import HowItWorks from "@/components/HowItWorks";
import BenefitsSection from "@/components/BenefitsSection";
import CommunitySection from "@/components/CommunitySection";

const Index = () => {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen deep-dark-bg">
      <Navbar />
      <HeroSection onStartLearning={() => navigate("/start-learning")} />
      <HowItWorks />
      <BenefitsSection />
      <CommunitySection />
    </div>
  );
};

export default Index;
