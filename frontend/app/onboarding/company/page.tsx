"use client";

import { useState, useEffect, useRef } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { ArrowLeft, Send, Sparkles, CheckCircle2 } from "lucide-react";
import { useRouter } from "next/navigation";

type Message = {
  role: "agent" | "user";
  content: string;
  timestamp: Date;
};

type Phase = {
  id: number;
  name: string;
  completed: boolean;
  icon: string;
};

const PHASES: Phase[] = [
  { id: 1, name: "Company & Role Overview", completed: false, icon: "🏢" },
  { id: 2, name: "Required Skills & Experience", completed: false, icon: "🎯" },
  { id: 3, name: "Team & Culture", completed: false, icon: "👥" },
  { id: 4, name: "Compensation & Benefits", completed: false, icon: "💰" },
  { id: 5, name: "Work Arrangements", completed: false, icon: "🌍" },
  { id: 6, name: "Screening Criteria", completed: false, icon: "✅" },
];

const SAMPLE_CONVERSATION = [
  {
    phase: 1,
    questions: [
      "Hi! I'm your company's AI agent. I'll be screening candidates and conducting conversations to find the TOP 3 best fits. Let's start by learning about your company. What's your company name and what do you do?",
      "Great! Tell me about the role you're hiring for. What's the job title?",
      "What are the main responsibilities for this position?",
    ],
  },
  {
    phase: 2,
    questions: [
      "What are the must-have technical skills for this role?",
      "How many years of experience are you looking for?",
      "Are there any specific technologies or tools the candidate should be familiar with?",
    ],
  },
  {
    phase: 3,
    questions: [
      "Tell me about your team. How many people will they work with?",
      "What's your company culture like?",
      "What qualities make someone successful on your team?",
    ],
  },
  {
    phase: 4,
    questions: [
      "What's the salary range for this position?",
      "Do you offer equity or stock options?",
      "What benefits do you provide? (health insurance, 401k, PTO, etc.)",
    ],
  },
  {
    phase: 5,
    questions: [
      "Where is this position located?",
      "Is this role remote, hybrid, or in-office?",
      "If hybrid, how many days per week in-office?",
    ],
  },
  {
    phase: 6,
    questions: [
      "What are absolute deal-breakers that would disqualify a candidate?",
      "What interview process will candidates go through after agent screening?",
      "Great! Let me calculate your agent's readiness score...",
    ],
  },
];

export default function CompanyOnboardingPage() {
  const router = useRouter();
  const [messages, setMessages] = useState<Message[]>([]);
  const [currentInput, setCurrentInput] = useState("");
  const [currentPhase, setCurrentPhase] = useState(1);
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [phases, setPhases] = useState(PHASES);
  const [isTyping, setIsTyping] = useState(false);
  const [readinessScore, setReadinessScore] = useState(0);
  const [showCompletion, setShowCompletion] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    // Start with first question
    const timer = setTimeout(() => {
      askNextQuestion();
    }, 1000);
    return () => clearTimeout(timer);
  }, []);

  const askNextQuestion = () => {
    const phaseData = SAMPLE_CONVERSATION[currentPhase - 1];
    if (phaseData && currentQuestionIndex < phaseData.questions.length) {
      setIsTyping(true);
      setTimeout(() => {
        setMessages((prev) => [
          ...prev,
          {
            role: "agent",
            content: phaseData.questions[currentQuestionIndex],
            timestamp: new Date(),
          },
        ]);
        setIsTyping(false);
      }, 1000);
    }
  };

  const handleSend = () => {
    if (!currentInput.trim()) return;

    // Add user message
    setMessages((prev) => [
      ...prev,
      {
        role: "user",
        content: currentInput,
        timestamp: new Date(),
      },
    ]);
    setCurrentInput("");

    // Move to next question
    const phaseData = SAMPLE_CONVERSATION[currentPhase - 1];
    const nextQuestionIndex = currentQuestionIndex + 1;

    if (nextQuestionIndex < phaseData.questions.length) {
      // More questions in current phase
      setCurrentQuestionIndex(nextQuestionIndex);
      setTimeout(() => askNextQuestion(), 1500);
    } else {
      // Complete current phase, move to next
      const updatedPhases = [...phases];
      updatedPhases[currentPhase - 1].completed = true;
      setPhases(updatedPhases);

      // Calculate readiness score progressively
      const score = Math.round(((currentPhase) / 6) * 100);
      setReadinessScore(score);

      if (currentPhase < 6) {
        // Move to next phase
        setCurrentPhase(currentPhase + 1);
        setCurrentQuestionIndex(0);
        setTimeout(() => {
          setMessages((prev) => [
            ...prev,
            {
              role: "agent",
              content: `Great! Phase ${currentPhase} completed. Let's move to the next phase.`,
              timestamp: new Date(),
            },
          ]);
          setTimeout(() => askNextQuestion(), 2000);
        }, 1500);
      } else {
        // All phases complete
        setTimeout(() => {
          setMessages((prev) => [
            ...prev,
            {
              role: "agent",
              content: `Perfect! Your readiness score is ${100}%. You're all set! Your agent is now ready to screen candidates and find your TOP 3 matches.`,
              timestamp: new Date(),
            },
          ]);
          setReadinessScore(100);
          setShowCompletion(true);
        }, 2000);
      }
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-50 via-white to-blue-50">
      {/* Header */}
      <header className="border-b bg-white/80 backdrop-blur-sm sticky top-0 z-10">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Button
                variant="ghost"
                size="icon"
                onClick={() => router.push("/")}
              >
                <ArrowLeft className="h-5 w-5" />
              </Button>
              <div className="flex items-center gap-2">
                <Sparkles className="h-6 w-6 text-purple-600" />
                <h1 className="text-xl font-bold">Agent Onboarding - Company</h1>
              </div>
            </div>
            <div className="flex items-center gap-4">
              <div className="text-sm">
                <span className="font-medium">Readiness:</span>{" "}
                <span className={`font-bold ${readinessScore >= 80 ? 'text-green-600' : 'text-orange-600'}`}>
                  {readinessScore}%
                </span>
              </div>
            </div>
          </div>
        </div>
      </header>

      <div className="container mx-auto px-4 py-8">
        <div className="grid lg:grid-cols-[300px_1fr] gap-8 max-w-7xl mx-auto">
          {/* Phase Sidebar */}
          <div className="space-y-4">
            <Card>
              <CardContent className="p-4">
                <h3 className="font-semibold mb-4 text-sm">Interview Phases</h3>
                <div className="space-y-3">
                  {phases.map((phase) => (
                    <div
                      key={phase.id}
                      className={`flex items-start gap-2 p-2 rounded-lg transition-colors ${
                        phase.id === currentPhase
                          ? "bg-purple-50 border border-purple-200"
                          : phase.completed
                          ? "bg-green-50"
                          : "bg-gray-50"
                      }`}
                    >
                      <div className="text-lg">{phase.icon}</div>
                      <div className="flex-1 min-w-0">
                        <div className="text-xs font-medium leading-tight">
                          {phase.name}
                        </div>
                      </div>
                      {phase.completed && (
                        <CheckCircle2 className="h-4 w-4 text-green-600 flex-shrink-0" />
                      )}
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Chat Area */}
          <Card className="flex flex-col h-[calc(100vh-200px)]">
            <CardContent className="flex-1 p-6 overflow-y-auto">
              <div className="space-y-4">
                {messages.map((message, index) => (
                  <div
                    key={index}
                    className={`flex ${
                      message.role === "user" ? "justify-end" : "justify-start"
                    }`}
                  >
                    <div
                      className={`max-w-[80%] rounded-2xl px-4 py-3 ${
                        message.role === "user"
                          ? "bg-purple-600 text-white"
                          : "bg-gray-100 text-gray-900"
                      }`}
                    >
                      <div className="text-sm">{message.content}</div>
                      <div
                        className={`text-xs mt-1 ${
                          message.role === "user"
                            ? "text-purple-100"
                            : "text-gray-500"
                        }`}
                      >
                        {message.timestamp.toLocaleTimeString([], {
                          hour: "2-digit",
                          minute: "2-digit",
                        })}
                      </div>
                    </div>
                  </div>
                ))}
                {isTyping && (
                  <div className="flex justify-start">
                    <div className="bg-gray-100 rounded-2xl px-4 py-3">
                      <div className="flex gap-1">
                        <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
                        <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
                        <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
                      </div>
                    </div>
                  </div>
                )}
                <div ref={messagesEndRef} />
              </div>
            </CardContent>

            {/* Input Area */}
            {!showCompletion && (
              <div className="border-t p-4">
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={currentInput}
                    onChange={(e) => setCurrentInput(e.target.value)}
                    onKeyPress={(e) => e.key === "Enter" && handleSend()}
                    placeholder="Type your answer..."
                    className="flex-1 px-4 py-3 border rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-600"
                  />
                  <Button
                    size="lg"
                    onClick={handleSend}
                    className="bg-purple-600 hover:bg-purple-700"
                    disabled={!currentInput.trim()}
                  >
                    <Send className="h-5 w-5" />
                  </Button>
                </div>
              </div>
            )}

            {/* Completion CTA */}
            {showCompletion && (
              <div className="border-t p-6 bg-gradient-to-r from-purple-50 to-blue-50">
                <div className="text-center space-y-4">
                  <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto">
                    <CheckCircle2 className="h-8 w-8 text-green-600" />
                  </div>
                  <div>
                    <h3 className="text-lg font-semibold mb-2">
                      Your Agent is Ready!
                    </h3>
                    <p className="text-sm text-muted-foreground mb-4">
                      Your AI agent will now start screening candidates to find
                      your TOP 3 matches.
                    </p>
                  </div>
                  <Button
                    size="lg"
                    onClick={() => router.push("/dashboard/company")}
                    className="bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700"
                  >
                    Go to Dashboard
                    <Sparkles className="ml-2 h-4 w-4" />
                  </Button>
                </div>
              </div>
            )}
          </Card>
        </div>
      </div>
    </div>
  );
}
