"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Sparkles, MessageSquare, TrendingUp, CheckCircle2, Eye, Calendar, ArrowRight, Activity } from "lucide-react";
import { useRouter } from "next/navigation";

type Match = {
  id: string;
  company: string;
  role: string;
  mutualScore: number;
  talentScore: number;
  companyScore: number;
  conversationTurns: number;
  topInsights: string[];
  status: "completed" | "in_progress";
};

const DEMO_MATCHES: Match[] = [
  {
    id: "1",
    company: "TechCorp",
    role: "Senior Software Engineer",
    mutualScore: 94,
    talentScore: 96,
    companyScore: 94,
    conversationTurns: 12,
    topInsights: [
      "Strong match on distributed systems expertise",
      "Culture fit: async-first remote work",
      "Growth path aligns with your 3-year goals",
    ],
    status: "completed",
  },
  {
    id: "2",
    company: "StartupXYZ",
    role: "Lead Developer",
    mutualScore: 91,
    talentScore: 93,
    companyScore: 91,
    conversationTurns: 10,
    topInsights: [
      "Excited about your microservices experience",
      "Equity package matches your expectations",
      "Team size and autonomy level ideal for you",
    ],
    status: "completed",
  },
  {
    id: "3",
    company: "BigTech Inc",
    role: "Staff Engineer",
    mutualScore: 88,
    talentScore: 88,
    companyScore: 92,
    conversationTurns: 11,
    topInsights: [
      "Strong technical match on cloud architecture",
      "Hybrid schedule (2 days/week) acceptable",
      "Learning budget and conference attendance included",
    ],
    status: "completed",
  },
];

export default function TalentDashboardPage() {
  const router = useRouter();
  const [conversationsToday, setConversationsToday] = useState(23);
  const [activeConversations, setActiveConversations] = useState(3);
  const [matches, setMatches] = useState(DEMO_MATCHES);
  const [isAgentWorking, setIsAgentWorking] = useState(true);

  // Simulate real-time updates
  useEffect(() => {
    const interval = setInterval(() => {
      setConversationsToday((prev) => prev + Math.floor(Math.random() * 2));
      if (Math.random() > 0.7) {
        setActiveConversations((prev) => Math.max(0, prev + (Math.random() > 0.5 ? 1 : -1)));
      }
    }, 5000);

    // Stop agent after some time for demo
    const stopTimer = setTimeout(() => {
      setIsAgentWorking(false);
      setActiveConversations(0);
    }, 30000);

    return () => {
      clearInterval(interval);
      clearTimeout(stopTimer);
    };
  }, []);

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50">
      {/* Header */}
      <header className="border-b bg-white/80 backdrop-blur-sm sticky top-0 z-10">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Sparkles className="h-8 w-8 text-blue-600" />
              <h1 className="text-2xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
                Nexus AI
              </h1>
            </div>
            <div className="flex items-center gap-4">
              <span className="text-sm text-muted-foreground">Talent Dashboard</span>
            </div>
          </div>
        </div>
      </header>

      <div className="container mx-auto px-4 py-8">
        <div className="max-w-7xl mx-auto space-y-8">
          {/* Agent Status */}
          <Card className="border-2 border-blue-200 bg-gradient-to-r from-blue-50 to-purple-50">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <div className={`w-16 h-16 rounded-full ${isAgentWorking ? 'bg-green-100' : 'bg-gray-100'} flex items-center justify-center`}>
                    {isAgentWorking ? (
                      <Activity className="h-8 w-8 text-green-600 animate-pulse" />
                    ) : (
                      <CheckCircle2 className="h-8 w-8 text-gray-600" />
                    )}
                  </div>
                  <div>
                    <h2 className="text-2xl font-bold">
                      {isAgentWorking ? "Your Agent is Working" : "Agent Analysis Complete"}
                    </h2>
                    <p className="text-muted-foreground">
                      {isAgentWorking
                        ? "Conducting intelligent conversations to find your perfect match"
                        : "Your TOP 3 matches are ready for review"}
                    </p>
                  </div>
                </div>
                {isAgentWorking && (
                  <div className="flex items-center gap-2">
                    <span className="inline-block w-3 h-3 bg-green-500 rounded-full animate-pulse" />
                    <span className="text-sm font-medium text-green-700">Active</span>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Stats Grid */}
          <div className="grid md:grid-cols-3 gap-6">
            <Card>
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-sm font-medium text-muted-foreground">
                    Conversations Today
                  </CardTitle>
                  <MessageSquare className="h-5 w-5 text-blue-600" />
                </div>
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-bold text-blue-600">{conversationsToday}</div>
                <p className="text-xs text-muted-foreground mt-1">
                  {activeConversations} in progress
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-sm font-medium text-muted-foreground">
                    Matches Found
                  </CardTitle>
                  <TrendingUp className="h-5 w-5 text-green-600" />
                </div>
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-bold text-green-600">{matches.length}</div>
                <p className="text-xs text-muted-foreground mt-1">
                  All above 85% mutual score
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-sm font-medium text-muted-foreground">
                    Ready for Review
                  </CardTitle>
                  <CheckCircle2 className="h-5 w-5 text-purple-600" />
                </div>
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-bold text-purple-600">3</div>
                <p className="text-xs text-muted-foreground mt-1">
                  TOP 3 mutual matches
                </p>
              </CardContent>
            </Card>
          </div>

          {/* TOP 3 Matches */}
          <div>
            <div className="flex items-center justify-between mb-6">
              <div>
                <h2 className="text-2xl font-bold">TOP 3 Matches</h2>
                <p className="text-muted-foreground">
                  These companies are mutually interested based on deep compatibility analysis
                </p>
              </div>
            </div>

            <div className="space-y-4">
              {matches.map((match, index) => (
                <Card key={match.id} className="hover:shadow-lg transition-shadow">
                  <CardHeader>
                    <div className="flex items-start justify-between">
                      <div className="flex items-start gap-4">
                        <div className="w-12 h-12 bg-gradient-to-br from-blue-600 to-purple-600 text-white rounded-full flex items-center justify-center text-xl font-bold flex-shrink-0">
                          #{index + 1}
                        </div>
                        <div>
                          <CardTitle className="text-xl">{match.company}</CardTitle>
                          <CardDescription className="text-base mt-1">
                            {match.role}
                          </CardDescription>
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="text-3xl font-bold text-green-600">
                          {match.mutualScore}
                        </div>
                        <div className="text-xs text-muted-foreground">
                          Mutual Score
                        </div>
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    {/* Score Breakdown */}
                    <div className="grid grid-cols-2 gap-4 p-4 bg-gray-50 rounded-lg">
                      <div>
                        <div className="text-sm text-muted-foreground">Your Interest</div>
                        <div className="text-2xl font-bold text-blue-600">
                          {match.talentScore}%
                        </div>
                      </div>
                      <div>
                        <div className="text-sm text-muted-foreground">Their Interest</div>
                        <div className="text-2xl font-bold text-purple-600">
                          {match.companyScore}%
                        </div>
                      </div>
                    </div>

                    {/* Top Insights */}
                    <div>
                      <h4 className="font-semibold mb-2 text-sm">Key Insights</h4>
                      <div className="space-y-2">
                        {match.topInsights.map((insight, i) => (
                          <div key={i} className="flex items-start gap-2">
                            <CheckCircle2 className="h-4 w-4 text-green-600 flex-shrink-0 mt-0.5" />
                            <span className="text-sm">{insight}</span>
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* Conversation Stats */}
                    <div className="flex items-center gap-4 text-sm text-muted-foreground">
                      <span>{match.conversationTurns} conversation turns</span>
                      <span>•</span>
                      <span>{match.status === "completed" ? "Analysis complete" : "In progress"}</span>
                    </div>

                    {/* Actions */}
                    <div className="flex gap-3 pt-2">
                      <Button
                        className="flex-1"
                        variant="outline"
                        onClick={() => router.push(`/conversation/${match.id}`)}
                      >
                        <Eye className="mr-2 h-4 w-4" />
                        View Conversation
                      </Button>
                      <Button
                        className="flex-1 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700"
                        onClick={() => router.push(`/schedule/${match.id}`)}
                      >
                        <Calendar className="mr-2 h-4 w-4" />
                        Schedule Meeting
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>

          {/* How It Worked */}
          <Card>
            <CardHeader>
              <CardTitle>How Your Agent Found These Matches</CardTitle>
              <CardDescription>
                Your AI agent conducted {conversationsToday} conversations using a 3-phase strategy
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid md:grid-cols-3 gap-6">
                <div>
                  <div className="font-semibold mb-2">Phase 1: Screening</div>
                  <p className="text-sm text-muted-foreground">
                    Quick 2-3 turn conversations to identify deal-breakers and basic compatibility
                  </p>
                </div>
                <div>
                  <div className="font-semibold mb-2">Phase 2: Deep Dive</div>
                  <p className="text-sm text-muted-foreground">
                    5-7 turn detailed exploration of skills, culture fit, and mutual expectations
                  </p>
                </div>
                <div>
                  <div className="font-semibold mb-2">Phase 3: Verification</div>
                  <p className="text-sm text-muted-foreground">
                    3-4 turn final confirmation of interest level and compatibility scores
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
