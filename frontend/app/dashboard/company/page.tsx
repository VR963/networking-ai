"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Sparkles, MessageSquare, TrendingUp, CheckCircle2, Eye, Calendar, Activity } from "lucide-react";
import { useRouter } from "next/navigation";

type Candidate = {
  id: string;
  name: string;
  title: string;
  mutualScore: number;
  talentScore: number;
  companyScore: number;
  conversationTurns: number;
  topInsights: string[];
  status: "completed" | "in_progress";
};

const DEMO_CANDIDATES: Candidate[] = [
  {
    id: "1",
    name: "Alex Chen",
    title: "5 years exp, Distributed Systems Expert",
    mutualScore: 94,
    talentScore: 96,
    companyScore: 94,
    conversationTurns: 12,
    topInsights: [
      "Expert in microservices architecture (5 years)",
      "Async-first communication - matches your culture",
      "Excited about K8s and gRPC stack",
    ],
    status: "completed",
  },
  {
    id: "2",
    name: "Jordan Smith",
    title: "7 years exp, Cloud Architecture Specialist",
    mutualScore: 91,
    talentScore: 91,
    companyScore: 93,
    conversationTurns: 10,
    topInsights: [
      "Led multiple cloud migrations successfully",
      "Strong mentorship experience",
      "Open to hybrid work (2 days/week)",
    ],
    status: "completed",
  },
  {
    id: "3",
    name: "Sam Patel",
    title: "4 years exp, Full-Stack with Backend Focus",
    mutualScore: 88,
    talentScore: 92,
    companyScore: 88,
    conversationTurns: 11,
    topInsights: [
      "Experience with event-driven architectures",
      "Looking for Staff Engineer growth path",
      "Interested in technical leadership",
    ],
    status: "completed",
  },
];

export default function CompanyDashboardPage() {
  const router = useRouter();
  const [conversationsToday, setConversationsToday] = useState(47);
  const [activeScreening, setActiveScreening] = useState(5);
  const [candidates, setCandidates] = useState(DEMO_CANDIDATES);
  const [isAgentWorking, setIsAgentWorking] = useState(true);

  // Simulate real-time updates
  useEffect(() => {
    const interval = setInterval(() => {
      setConversationsToday((prev) => prev + Math.floor(Math.random() * 2));
      if (Math.random() > 0.7) {
        setActiveScreening((prev) => Math.max(0, prev + (Math.random() > 0.5 ? 1 : -1)));
      }
    }, 5000);

    // Stop agent after some time for demo
    const stopTimer = setTimeout(() => {
      setIsAgentWorking(false);
      setActiveScreening(0);
    }, 30000);

    return () => {
      clearInterval(interval);
      clearTimeout(stopTimer);
    };
  }, []);

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-50 via-white to-blue-50">
      {/* Header */}
      <header className="border-b bg-white/80 backdrop-blur-sm sticky top-0 z-10">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Sparkles className="h-8 w-8 text-purple-600" />
              <h1 className="text-2xl font-bold bg-gradient-to-r from-purple-600 to-blue-600 bg-clip-text text-transparent">
                Nexus AI
              </h1>
            </div>
            <div className="flex items-center gap-4">
              <span className="text-sm text-muted-foreground">Company Dashboard</span>
            </div>
          </div>
        </div>
      </header>

      <div className="container mx-auto px-4 py-8">
        <div className="max-w-7xl mx-auto space-y-8">
          {/* Agent Status */}
          <Card className="border-2 border-purple-200 bg-gradient-to-r from-purple-50 to-blue-50">
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
                      {isAgentWorking ? "Your Agent is Screening" : "Screening Complete"}
                    </h2>
                    <p className="text-muted-foreground">
                      {isAgentWorking
                        ? "Conducting intelligent conversations to find the best candidates"
                        : "Your TOP 3 candidates are ready for review"}
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

          {/* Job Posting Summary */}
          <Card>
            <CardHeader>
              <CardTitle>Active Job Posting</CardTitle>
              <CardDescription>Senior Software Engineer - Backend Systems</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid md:grid-cols-4 gap-4">
                <div>
                  <div className="text-sm text-muted-foreground mb-1">Location</div>
                  <div className="font-semibold">San Francisco, CA (Hybrid)</div>
                </div>
                <div>
                  <div className="text-sm text-muted-foreground mb-1">Salary Range</div>
                  <div className="font-semibold">$180k - $210k + Equity</div>
                </div>
                <div>
                  <div className="text-sm text-muted-foreground mb-1">Experience</div>
                  <div className="font-semibold">5+ years</div>
                </div>
                <div>
                  <div className="text-sm text-muted-foreground mb-1">Posted</div>
                  <div className="font-semibold">2 days ago</div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Stats Grid */}
          <div className="grid md:grid-cols-3 gap-6">
            <Card>
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-sm font-medium text-muted-foreground">
                    Candidates Screened
                  </CardTitle>
                  <MessageSquare className="h-5 w-5 text-purple-600" />
                </div>
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-bold text-purple-600">{conversationsToday}</div>
                <p className="text-xs text-muted-foreground mt-1">
                  {activeScreening} currently being screened
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-sm font-medium text-muted-foreground">
                    Qualified Matches
                  </CardTitle>
                  <TrendingUp className="h-5 w-5 text-green-600" />
                </div>
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-bold text-green-600">{candidates.length}</div>
                <p className="text-xs text-muted-foreground mt-1">
                  All above 85% mutual score
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-sm font-medium text-muted-foreground">
                    Ready to Interview
                  </CardTitle>
                  <CheckCircle2 className="h-5 w-5 text-blue-600" />
                </div>
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-bold text-blue-600">3</div>
                <p className="text-xs text-muted-foreground mt-1">
                  TOP 3 candidates selected
                </p>
              </CardContent>
            </Card>
          </div>

          {/* TOP 3 Candidates */}
          <div>
            <div className="flex items-center justify-between mb-6">
              <div>
                <h2 className="text-2xl font-bold">TOP 3 Candidates</h2>
                <p className="text-muted-foreground">
                  Pre-screened and mutually interested candidates ready for interviews
                </p>
              </div>
            </div>

            <div className="space-y-4">
              {candidates.map((candidate, index) => (
                <Card key={candidate.id} className="hover:shadow-lg transition-shadow">
                  <CardHeader>
                    <div className="flex items-start justify-between">
                      <div className="flex items-start gap-4">
                        <div className="w-12 h-12 bg-gradient-to-br from-purple-600 to-blue-600 text-white rounded-full flex items-center justify-center text-xl font-bold flex-shrink-0">
                          #{index + 1}
                        </div>
                        <div>
                          <CardTitle className="text-xl">{candidate.name}</CardTitle>
                          <CardDescription className="text-base mt-1">
                            {candidate.title}
                          </CardDescription>
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="text-3xl font-bold text-green-600">
                          {candidate.mutualScore}
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
                        <div className="text-sm text-muted-foreground">Your Score</div>
                        <div className="text-2xl font-bold text-purple-600">
                          {candidate.companyScore}%
                        </div>
                      </div>
                      <div>
                        <div className="text-sm text-muted-foreground">Their Interest</div>
                        <div className="text-2xl font-bold text-blue-600">
                          {candidate.talentScore}%
                        </div>
                      </div>
                    </div>

                    {/* Top Insights */}
                    <div>
                      <h4 className="font-semibold mb-2 text-sm">Key Insights</h4>
                      <div className="space-y-2">
                        {candidate.topInsights.map((insight, i) => (
                          <div key={i} className="flex items-start gap-2">
                            <CheckCircle2 className="h-4 w-4 text-green-600 flex-shrink-0 mt-0.5" />
                            <span className="text-sm">{insight}</span>
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* Conversation Stats */}
                    <div className="flex items-center gap-4 text-sm text-muted-foreground">
                      <span>{candidate.conversationTurns} conversation turns</span>
                      <span>•</span>
                      <span>{candidate.status === "completed" ? "Screening complete" : "In progress"}</span>
                    </div>

                    {/* Actions */}
                    <div className="flex gap-3 pt-2">
                      <Button
                        className="flex-1"
                        variant="outline"
                        onClick={() => router.push(`/conversation/${candidate.id}`)}
                      >
                        <Eye className="mr-2 h-4 w-4" />
                        View Screening
                      </Button>
                      <Button
                        className="flex-1 bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700"
                        onClick={() => router.push(`/schedule/${candidate.id}`)}
                      >
                        <Calendar className="mr-2 h-4 w-4" />
                        Schedule Interview
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
              <CardTitle>How Your Agent Screened Candidates</CardTitle>
              <CardDescription>
                Your AI agent conducted {conversationsToday} conversations using a 3-phase strategy
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid md:grid-cols-3 gap-6">
                <div>
                  <div className="font-semibold mb-2">Phase 1: Screening</div>
                  <p className="text-sm text-muted-foreground">
                    Verified deal-breakers: timezone, hybrid work, salary expectations
                  </p>
                </div>
                <div>
                  <div className="font-semibold mb-2">Phase 2: Deep Dive</div>
                  <p className="text-sm text-muted-foreground">
                    Assessed technical skills, cultural fit, and career goals alignment
                  </p>
                </div>
                <div>
                  <div className="font-semibold mb-2">Phase 3: Verification</div>
                  <p className="text-sm text-muted-foreground">
                    Confirmed mutual interest and availability for interview process
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
