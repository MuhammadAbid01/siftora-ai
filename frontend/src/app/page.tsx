import { Nav } from "@/components/landing/nav";
import { Hero } from "@/components/landing/hero";
import { LogoStrip } from "@/components/landing/logo-strip";
import { Features } from "@/components/landing/features";
import { ProductMockup } from "@/components/landing/product-mockup";
import { Workflow } from "@/components/landing/workflow";
import { StatsBand } from "@/components/landing/stats-band";
import { WhyAgentic } from "@/components/landing/why-agentic";
import { SeededLeadExample } from "@/components/landing/seeded-lead-example";
import { ResponsibleOutreach } from "@/components/landing/responsible-outreach";
import { Testimonial } from "@/components/landing/testimonial";
import { TechStack } from "@/components/landing/tech-stack";
import { Footer } from "@/components/landing/footer";

export default function Home() {
  return (
    <div className="flex min-h-full flex-col">
      <Nav />
      <main className="flex-1">
        <Hero />
        <LogoStrip />
        <Features />
        <ProductMockup />
        <Workflow />
        <StatsBand />
        <WhyAgentic />
        <SeededLeadExample />
        <ResponsibleOutreach />
        <Testimonial />
        <TechStack />
      </main>
      <Footer />
    </div>
  );
}
