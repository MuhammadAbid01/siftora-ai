import { Nav } from "@/components/landing/nav";
import { Hero } from "@/components/landing/hero";
import { ProductMockup } from "@/components/landing/product-mockup";
import { Workflow } from "@/components/landing/workflow";
import { WhyAgentic } from "@/components/landing/why-agentic";
import { Features } from "@/components/landing/features";
import { SeededLeadExample } from "@/components/landing/seeded-lead-example";
import { ResponsibleOutreach } from "@/components/landing/responsible-outreach";
import { TechStack } from "@/components/landing/tech-stack";
import { Footer } from "@/components/landing/footer";

export default function Home() {
  return (
    <div className="flex min-h-full flex-col">
      <Nav />
      <main className="flex-1">
        <Hero />
        <ProductMockup />
        <Workflow />
        <WhyAgentic />
        <Features />
        <SeededLeadExample />
        <ResponsibleOutreach />
        <TechStack />
      </main>
      <Footer />
    </div>
  );
}
