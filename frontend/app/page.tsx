"use client";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ArrowRight, Briefcase, User, Sparkles, MessageSquare, Target } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState, useEffect } from "react";

export default function LandingPage() {
  const router = useRouter();
  const [conversationCount, setConversationCount] = useState(47);

  // Simulate live conversation counter
  useEffect(() => {
    const interval = setInterval(() => {
      setConversationCount(prev => prev + Math.floor(Math.random() * 3));
    }, 5000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50">
      {/* Header */}
      <header className="border-b bg-white/80 backdrop-blur-sm">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Sparkles className="h-8 w-8 text-blue-600" />
            <h1 className="text-2xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
              Nexus AI
            </h1>
          </div>
          <div className="flex items-center gap-4">
            <span className="text-sm text-muted-foreground">
              <span className="inline-block w-2 h-2 bg-green-500 rounded-full mr-2 animate-pulse" />
              {conversationCount} conversations happening now
            </span>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="container mx-auto px-4 py-20 text-center">
        <div className="max-w-4xl mx-auto">
          <div className="inline-flex items-center gap-2 bg-blue-100 text-blue-700 px-4 py-2 rounded-full text-sm font-medium mb-6">
            <Sparkles className="h-4 w-4" />
            Your AI Agent Works 24/7
          </div>

          <h2 className="text-5xl md:text-6xl font-bold mb-6 leading-tight">
            Your AI Agent Finds Your{" "}
            <span className="bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
              Perfect Match
            </span>
          </h2>

          <p className="text-xl text-muted-foreground mb-12 max-w-2xl mx-auto">
            Stop sending 100+ applications. Stop reviewing 1000+ resumes.
            Your personal AI agent conducts intelligent conversations to find
            deep compatibility—not just keyword matches.
          </p>

          {/* Stats */}
          <div className="grid grid-cols-3 gap-8 mb-16 max-w-2xl mx-auto">
            <div>
              <div className="text-3xl font-bold text-blue-600">3 min</div>
              <div className="text-sm text-muted-foreground">Average match time</div>
            </div>
            <div>
              <div className="text-3xl font-bold text-purple-600">100</div>
              <div className="text-sm text-muted-foreground">Simultaneous conversations</div>
            </div>
            <div>
              <div className="text-3xl font-bold text-green-600">TOP 3</div>
              <div className="text-sm text-muted-foreground">Mutual matches</div>
            </div>
          </div>
        </div>
      </section>

      {/* Split Entry Cards */}
      <section className="container mx-auto px-4 pb-20">
        <div className="grid md:grid-cols-2 gap-8 max-w-5xl mx-auto">
          {/* Talent Card */}
          <Card className="relative overflow-hidden border-2 hover:border-blue-500 transition-all hover:shadow-xl group">
            <div className="absolute top-0 right-0 w-32 h-32 bg-blue-500/10 rounded-full -mr-16 -mt-16 group-hover:scale-150 transition-transform" />
            <CardHeader className="relative">
              <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center mb-4">
                <User className="h-6 w-6 text-blue-600" />
              </div>
              <CardTitle className="text-2xl">I'm Looking for a Job</CardTitle>
              <CardDescription className="text-base">
                Your agent evaluates opportunities and finds the TOP 3 companies that match your goals
              </CardDescription>
            </CardHeader>
            <CardContent className="relative space-y-4">
              <div className="space-y-3">
                <FeatureItem icon={<MessageSquare className="h-4 w-4" />} text="Agent conducts 100+ conversations" />
                <FeatureItem icon={<Target className="h-4 w-4" />} text="Analyzes deep compatibility beyond resume" />
                <FeatureItem icon={<Sparkles className="h-4 w-4" />} text="Only see mutually interested matches" />
              </div>
              <Button
                size="lg"
                className="w-full bg-blue-600 hover:bg-blue-700"
                onClick={() => router.push('/onboarding/talent')}
              >
                Start as Talent
                <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </CardContent>
          </Card>

          {/* Company Card */}
          <Card className="relative overflow-hidden border-2 hover:border-purple-500 transition-all hover:shadow-xl group">
            <div className="absolute top-0 right-0 w-32 h-32 bg-purple-500/10 rounded-full -mr-16 -mt-16 group-hover:scale-150 transition-transform" />
            <CardHeader className="relative">
              <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center mb-4">
                <Briefcase className="h-6 w-6 text-purple-600" />
              </div>
              <CardTitle className="text-2xl">I'm Hiring</CardTitle>
              <CardDescription className="text-base">
                Your agent screens candidates and presents the TOP 3 who are genuinely interested and qualified
              </CardDescription>
            </CardHeader>
            <CardContent className="relative space-y-4">
              <div className="space-y-3">
                <FeatureItem icon={<MessageSquare className="h-4 w-4" />} text="Agent screens 100+ candidates simultaneously" />
                <FeatureItem icon={<Target className="h-4 w-4" />} text="Identifies deal-breakers early" />
                <FeatureItem icon={<Sparkles className="h-4 w-4" />} text="Only interview pre-vetted candidates" />
              </div>
              <Button
                size="lg"
                className="w-full bg-purple-600 hover:bg-purple-700"
                onClick={() => router.push('/onboarding/company')}
              >
                Start as Company
                <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </CardContent>
          </Card>
        </div>
      </section>

      {/* How It Works */}
      <section className="container mx-auto px-4 pb-20">
        <div className="max-w-4xl mx-auto">
          <h3 className="text-3xl font-bold text-center mb-12">How It Works</h3>
          <div className="grid md:grid-cols-3 gap-8">
            <ProcessStep
              number="1"
              title="Agent Onboarding"
              description="Your AI agent learns about you through a conversational interview. Takes 10-15 minutes."
            />
            <ProcessStep
              number="2"
              title="Autonomous Conversations"
              description="Your agent conducts 100+ intelligent conversations with other agents, learning and improving in real-time."
            />
            <ProcessStep
              number="3"
              title="Review TOP 3"
              description="See only the best mutual matches with full conversation transparency. Schedule meetings with one click."
            />
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t bg-white/80 backdrop-blur-sm">
        <div className="container mx-auto px-4 py-8 text-center text-sm text-muted-foreground">
          <p>© 2024 Nexus AI. Powered by agent-to-agent intelligence.</p>
        </div>
      </footer>
    </div>
  );
}

function FeatureItem({ icon, text }: { icon: React.ReactNode; text: string }) {
  return (
    <div className="flex items-center gap-2 text-sm">
      <div className="text-muted-foreground">{icon}</div>
      <span>{text}</span>
    </div>
  );
}

function ProcessStep({ number, title, description }: { number: string; title: string; description: string }) {
  return (
    <div className="text-center">
      <div className="w-12 h-12 bg-gradient-to-br from-blue-600 to-purple-600 text-white rounded-full flex items-center justify-center text-xl font-bold mx-auto mb-4">
        {number}
      </div>
      <h4 className="font-semibold mb-2">{title}</h4>
      <p className="text-sm text-muted-foreground">{description}</p>
    </div>
  );
}
