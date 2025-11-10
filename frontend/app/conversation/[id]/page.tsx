"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ArrowLeft, CheckCircle2, XCircle, AlertCircle, TrendingUp, Calendar } from "lucide-react";
import { useRouter, useParams } from "next/navigation";

type ConversationTurn = {
  turnNumber: number;
  phase: "screening" | "deep_dive" | "verification";
  question: string;
  response: string;
  insightExtracted: string;
  sentiment: "positive" | "neutral" | "negative";
};

type DealBreaker = {
  checked: string;
  result: "passed" | "concern";
};

const DEMO_CONVERSATION: ConversationTurn[] = [
  {
    turnNumber: 1,
    phase: "screening",
    question: "What's your experience with distributed systems and microservices architecture?",
    response: "I have 5 years of hands-on experience building and scaling microservices at my current company. Led the migration from monolith to microservices handling 10M+ requests/day.",
    insightExtracted: "Expert-level distributed systems experience (5 years)",
    sentiment: "positive",
  },
  {
    turnNumber: 2,
    phase: "screening",
    question: "TechCorp operates on PST hours with core hours 10am-3pm PST. Can you accommodate this schedule?",
    response: "Yes, absolutely. I'm currently on EST but happy to shift my hours to align with PST for team collaboration.",
    insightExtracted: "Willing and able to work PST hours",
    sentiment: "positive",
  },
  {
    turnNumber: 3,
    phase: "screening",
    question: "The role requires 2 days per week in our San Francisco office. Is this feasible for you?",
    response: "I'm open to hybrid work. I'd need to relocate to SF area, but I've been considering that move anyway.",
    insightExtracted: "Open to hybrid (2 days/week) and SF relocation",
    sentiment: "positive",
  },
  {
    turnNumber: 4,
    phase: "deep_dive",
    question: "Tell me about how you approach system design and architectural decisions.",
    response: "I believe in starting with requirements and constraints, then iterating on design. I prefer documenting decisions in ADRs (Architecture Decision Records) and getting team input before finalizing.",
    insightExtracted: "Thoughtful, collaborative approach to architecture - matches TechCorp's culture",
    sentiment: "positive",
  },
  {
    turnNumber: 5,
    phase: "deep_dive",
    question: "What's your preferred way of working with a team? Synchronous vs asynchronous communication?",
    response: "I strongly prefer async-first communication - detailed docs, clear written updates, and focused meeting time only when needed. I find this respects everyone's deep work time.",
    insightExtracted: "Async-first communication style - perfect match for TechCorp's remote culture",
    sentiment: "positive",
  },
  {
    turnNumber: 6,
    phase: "deep_dive",
    question: "Where do you see yourself in 3 years? What are your growth goals?",
    response: "I want to grow into a Staff Engineer role, focusing more on system architecture and mentoring. I'm interested in leading technical initiatives across multiple teams.",
    insightExtracted: "Growth path aligns with TechCorp's Staff Engineer track",
    sentiment: "positive",
  },
  {
    turnNumber: 7,
    phase: "deep_dive",
    question: "What technologies are you most excited to work with, and which would you prefer to avoid?",
    response: "Excited about: Kubernetes, gRPC, event-driven architectures. Would prefer to minimize PHP - I have experience but it's not where I want to focus my growth.",
    insightExtracted: "Tech stack alignment - TechCorp uses K8s and gRPC, minimal PHP",
    sentiment: "positive",
  },
  {
    turnNumber: 8,
    phase: "deep_dive",
    question: "TechCorp offers $180k-$210k base + equity. Does this align with your expectations?",
    response: "Yes, that's right in my target range. The equity component is important to me as I want to have real ownership in the company's success.",
    insightExtracted: "Compensation expectations align perfectly",
    sentiment: "positive",
  },
  {
    turnNumber: 9,
    phase: "verification",
    question: "On a scale of 1-10, how interested are you in this opportunity at TechCorp?",
    response: "Based on everything we've discussed, I'd say 9/10. The tech stack, culture, and growth opportunities all align really well with what I'm looking for.",
    insightExtracted: "Very high interest level (9/10)",
    sentiment: "positive",
  },
  {
    turnNumber: 10,
    phase: "verification",
    question: "If offered, would you be ready to start within 2-4 weeks?",
    response: "Yes, I can give 2 weeks notice and would be ready to start shortly after that.",
    insightExtracted: "Available within expected timeframe",
    sentiment: "positive",
  },
  {
    turnNumber: 11,
    phase: "verification",
    question: "Is there anything that would make you hesitant to accept an offer from TechCorp?",
    response: "Only thing would be if the relocation package wasn't competitive, but I saw that's negotiable and you offer relocation assistance.",
    insightExtracted: "Minor concern about relocation - addressable in offer negotiation",
    sentiment: "neutral",
  },
  {
    turnNumber: 12,
    phase: "verification",
    question: "Final question: What questions do you have for us that we haven't covered?",
    response: "I'd love to learn more about the team structure and who I'd be working with directly. Also curious about the onboarding process for new engineers.",
    insightExtracted: "Asking thoughtful questions about team dynamics and onboarding",
    sentiment: "positive",
  },
];

const DEAL_BREAKERS: DealBreaker[] = [
  { checked: "Willing to work PST hours", result: "passed" },
  { checked: "Open to hybrid (2 days/week in office)", result: "passed" },
  { checked: "Salary expectations align ($180k-$210k)", result: "passed" },
  { checked: "Available to start within 4 weeks", result: "passed" },
  { checked: "Open to San Francisco relocation", result: "concern" },
];

const POSITIVE_SIGNALS = [
  "Asked about growth opportunities (3 times)",
  "Excited about the tech stack (K8s, gRPC)",
  "Values work-life balance - matches company culture",
  "Strong preference for async communication",
  "Interested in mentoring and technical leadership",
];

export default function ConversationDetailPage() {
  const router = useRouter();
  const params = useParams();
  const [selectedPhase, setSelectedPhase] = useState<string>("all");

  const filteredConversation =
    selectedPhase === "all"
      ? DEMO_CONVERSATION
      : DEMO_CONVERSATION.filter((turn) => turn.phase === selectedPhase);

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50">
      {/* Header */}
      <header className="border-b bg-white/80 backdrop-blur-sm sticky top-0 z-10">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center gap-4">
            <Button
              variant="ghost"
              size="icon"
              onClick={() => router.back()}
            >
              <ArrowLeft className="h-5 w-5" />
            </Button>
            <div>
              <h1 className="text-xl font-bold">Conversation with TechCorp</h1>
              <p className="text-sm text-muted-foreground">
                Senior Software Engineer Position
              </p>
            </div>
          </div>
        </div>
      </header>

      <div className="container mx-auto px-4 py-8">
        <div className="max-w-6xl mx-auto space-y-6">
          {/* Score Summary */}
          <Card className="border-2 border-green-200 bg-gradient-to-r from-green-50 to-blue-50">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-2xl font-bold mb-2">Mutual Match Score</h2>
                  <p className="text-muted-foreground">
                    Both you and TechCorp are highly interested based on this conversation
                  </p>
                </div>
                <div className="text-center">
                  <div className="text-5xl font-bold text-green-600">94</div>
                  <div className="text-sm text-muted-foreground mt-1">out of 100</div>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4 mt-6">
                <div className="p-4 bg-white rounded-lg">
                  <div className="text-sm text-muted-foreground mb-1">
                    Your Interest Score
                  </div>
                  <div className="text-3xl font-bold text-blue-600">96</div>
                </div>
                <div className="p-4 bg-white rounded-lg">
                  <div className="text-sm text-muted-foreground mb-1">
                    Their Interest Score
                  </div>
                  <div className="text-3xl font-bold text-purple-600">94</div>
                </div>
              </div>
            </CardContent>
          </Card>

          <div className="grid lg:grid-cols-[300px_1fr] gap-6">
            {/* Sidebar - Insights */}
            <div className="space-y-4">
              {/* Deal Breakers */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Deal Breakers</CardTitle>
                </CardHeader>
                <CardContent className="space-y-2">
                  {DEAL_BREAKERS.map((item, i) => (
                    <div key={i} className="flex items-start gap-2">
                      {item.result === "passed" ? (
                        <CheckCircle2 className="h-4 w-4 text-green-600 flex-shrink-0 mt-0.5" />
                      ) : (
                        <AlertCircle className="h-4 w-4 text-orange-600 flex-shrink-0 mt-0.5" />
                      )}
                      <span className="text-sm">{item.checked}</span>
                    </div>
                  ))}
                </CardContent>
              </Card>

              {/* Positive Signals */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Positive Signals</CardTitle>
                </CardHeader>
                <CardContent className="space-y-2">
                  {POSITIVE_SIGNALS.map((signal, i) => (
                    <div key={i} className="flex items-start gap-2">
                      <TrendingUp className="h-4 w-4 text-green-600 flex-shrink-0 mt-0.5" />
                      <span className="text-sm">{signal}</span>
                    </div>
                  ))}
                </CardContent>
              </Card>

              {/* Action */}
              <Card>
                <CardContent className="p-4">
                  <Button
                    className="w-full bg-gradient-to-r from-blue-600 to-purple-600"
                    onClick={() => router.push(`/schedule/${params.id}`)}
                  >
                    <Calendar className="mr-2 h-4 w-4" />
                    Schedule Meeting
                  </Button>
                </CardContent>
              </Card>
            </div>

            {/* Main Content - Conversation */}
            <div className="space-y-4">
              {/* Phase Filter */}
              <Card>
                <CardContent className="p-4">
                  <div className="flex gap-2">
                    <Button
                      variant={selectedPhase === "all" ? "default" : "outline"}
                      size="sm"
                      onClick={() => setSelectedPhase("all")}
                    >
                      All Phases
                    </Button>
                    <Button
                      variant={selectedPhase === "screening" ? "default" : "outline"}
                      size="sm"
                      onClick={() => setSelectedPhase("screening")}
                    >
                      Screening
                    </Button>
                    <Button
                      variant={selectedPhase === "deep_dive" ? "default" : "outline"}
                      size="sm"
                      onClick={() => setSelectedPhase("deep_dive")}
                    >
                      Deep Dive
                    </Button>
                    <Button
                      variant={selectedPhase === "verification" ? "default" : "outline"}
                      size="sm"
                      onClick={() => setSelectedPhase("verification")}
                    >
                      Verification
                    </Button>
                  </div>
                </CardContent>
              </Card>

              {/* Conversation Turns */}
              <div className="space-y-4">
                {filteredConversation.map((turn) => (
                  <Card key={turn.turnNumber}>
                    <CardHeader>
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center text-sm font-bold text-blue-600">
                            {turn.turnNumber}
                          </div>
                          <div>
                            <CardTitle className="text-sm font-medium">
                              Turn {turn.turnNumber}
                            </CardTitle>
                            <CardDescription className="text-xs capitalize">
                              {turn.phase.replace("_", " ")} Phase
                            </CardDescription>
                          </div>
                        </div>
                        <div
                          className={`px-3 py-1 rounded-full text-xs font-medium ${
                            turn.sentiment === "positive"
                              ? "bg-green-100 text-green-700"
                              : turn.sentiment === "neutral"
                              ? "bg-gray-100 text-gray-700"
                              : "bg-red-100 text-red-700"
                          }`}
                        >
                          {turn.sentiment}
                        </div>
                      </div>
                    </CardHeader>
                    <CardContent className="space-y-4">
                      {/* Question */}
                      <div>
                        <div className="text-xs font-semibold text-muted-foreground mb-2">
                          COMPANY AGENT ASKED:
                        </div>
                        <div className="p-3 bg-purple-50 rounded-lg text-sm">
                          {turn.question}
                        </div>
                      </div>

                      {/* Response */}
                      <div>
                        <div className="text-xs font-semibold text-muted-foreground mb-2">
                          YOUR AGENT RESPONDED:
                        </div>
                        <div className="p-3 bg-blue-50 rounded-lg text-sm">
                          {turn.response}
                        </div>
                      </div>

                      {/* Insight */}
                      <div className="flex items-start gap-2 p-3 bg-green-50 rounded-lg">
                        <CheckCircle2 className="h-4 w-4 text-green-600 flex-shrink-0 mt-0.5" />
                        <div>
                          <div className="text-xs font-semibold text-green-700 mb-1">
                            INSIGHT EXTRACTED:
                          </div>
                          <div className="text-sm text-green-900">
                            {turn.insightExtracted}
                          </div>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
