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
              {conversationCount} conversations happening worldwide
            </span>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="container mx-auto px-4 py-16 text-center">
        <div className="max-w-3xl mx-auto">
          <h2 className="text-4xl md:text-5xl font-bold mb-6 leading-tight">
            Unlock the Potential of{" "}
            <span className="bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
              AI-Powered Matching
            </span>
          </h2>

          <p className="text-lg text-muted-foreground mb-12 max-w-2xl mx-auto">
            Tell us who you are and what you're looking for. Upload your documents
            and LinkedIn profile, and let AI work for your best interest.
          </p>
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
              <CardTitle className="text-2xl">Talent</CardTitle>
              <CardDescription className="text-base">
                Upload your profile, answer 6 questions, and let your AI agent find the perfect opportunities
              </CardDescription>
            </CardHeader>
            <CardContent className="relative space-y-4">
              <div className="space-y-3">
                <FeatureItem icon={<Sparkles className="h-4 w-4" />} text="AI analyzes your documents & profile" />
                <FeatureItem icon={<MessageSquare className="h-4 w-4" />} text="6 smart questions reveal your goals" />
                <FeatureItem icon={<Target className="h-4 w-4" />} text="Your agent works 24/7 for you" />
              </div>
              <Button
                size="lg"
                className="w-full bg-blue-600 hover:bg-blue-700"
                onClick={() => router.push('/upload')}
              >
                Get Started
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
              <CardTitle className="text-2xl">Hiring Manager</CardTitle>
              <CardDescription className="text-base">
                Define your role, answer 6 questions, and let your AI agent find the best talent
              </CardDescription>
            </CardHeader>
            <CardContent className="relative space-y-4">
              <div className="space-y-3">
                <FeatureItem icon={<Sparkles className="h-4 w-4" />} text="AI understands your requirements" />
                <FeatureItem icon={<MessageSquare className="h-4 w-4" />} text="6 smart questions define your needs" />
                <FeatureItem icon={<Target className="h-4 w-4" />} text="Your agent finds top matches 24/7" />
              </div>
              <Button
                size="lg"
                className="w-full bg-purple-600 hover:bg-purple-700"
                onClick={() => router.push('/upload')}
              >
                Get Started
                <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </CardContent>
          </Card>
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
