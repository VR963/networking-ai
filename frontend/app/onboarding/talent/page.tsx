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
  { id: 1, name: "Background & Role Preferences", completed: false, icon: "👤" },
  { id: 2, name: "Skills & Expertise", completed: false, icon: "🎯" },
  { id: 3, name: "Work Environment & Culture", completed: false, icon: "🏢" },
  { id: 4, name: "Growth & Development", completed: false, icon: "📈" },
  { id: 5, name: "Compensation & Benefits", completed: false, icon: "💰" },
  { id: 6, name: "Location & Flexibility", completed: false, icon: "🌍" },
  { id: 7, name: "Deal Breakers & Validation", completed: false, icon: "✅" },
];

const SAMPLE_CONVERSATION = [
  {
    phase: 1,
    questions: [
      "Hi! I'm your personal AI agent. I'll be representing you in conversations with company agents to find your perfect match. Let's start by learning about you. What kind of role are you looking for?",
      "That sounds great! What industries are you most interested in?",
      "Got it. How many years of experience do you have in this field?",
    ],
  },
  {
    phase: 2,
    questions: [
      "Let's dive into your skills. What are your top 3 technical skills?",
      "Excellent! Can you tell me about a recent project where you used these skills?",
      "What technologies or tools are you most excited to work with?",
    ],
  },
  {
    phase: 3,
    questions: [
      "Now let's talk about work environment. Do you prefer working in a startup or established company?",
      "What kind of team culture resonates with you most?",
      "How do you feel about remote work vs in-office?",
    ],
  },
  {
    phase: 4,
    questions: [
      "Let's discuss growth. What are your career goals for the next 2-3 years?",
      "What kind of learning opportunities are important to you?",
      "Do you prefer companies that offer formal training programs or self-directed learning?",
    ],
  },
  {
    phase: 5,
    questions: [
      "Let's talk about compensation. What's your expected salary range?",
      "Are equity or stock options important to you?",
      "What benefits are must-haves for you? (health insurance, 401k, etc.)",
    ],
  },
  {
    phase: 6,
    questions: [
      "Where are you located, and are you open to relocating?",
      "What's your ideal work schedule? (flexible hours, 9-5, etc.)",
      "How many days per week would you prefer to work in-office if required?",
    ],
  },
  {
    phase: 7,
    questions: [
      "Almost done! What are your absolute deal-breakers that would make you reject an opportunity?",
      "Is there anything else important I should know when representing you?",
      "Great! Let me calculate your readiness score...",
    ],
  },
];

export default function TalentOnboardingPage() {
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
      const score = Math.round(((currentPhase) / 7) * 100);
      setReadinessScore(score);

      if (currentPhase < 7) {
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
              content: `Perfect! Your readiness score is ${100}%. You're all set! Your agent is now ready to represent you in conversations with companies.`,
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
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50">
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
                <Sparkles className="h-6 w-6 text-blue-600" />
                <h1 className="text-xl font-bold">Agent Onboarding - Talent</h1>
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
                          ? "bg-blue-50 border border-blue-200"
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
                          ? "bg-blue-600 text-white"
                          : "bg-gray-100 text-gray-900"
                      }`}
                    >
                      <div className="text-sm">{message.content}</div>
                      <div
                        className={`text-xs mt-1 ${
                          message.role === "user"
                            ? "text-blue-100"
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
                    className="flex-1 px-4 py-3 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-600"
                  />
                  <Button
                    size="lg"
                    onClick={handleSend}
                    className="bg-blue-600 hover:bg-blue-700"
                    disabled={!currentInput.trim()}
                  >
                    <Send className="h-5 w-5" />
                  </Button>
                </div>
              </div>
            )}

            {/* Completion CTA */}
            {showCompletion && (
              <div className="border-t p-6 bg-gradient-to-r from-blue-50 to-purple-50">
                <div className="text-center space-y-4">
                  <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto">
                    <CheckCircle2 className="h-8 w-8 text-green-600" />
                  </div>
                  <div>
                    <h3 className="text-lg font-semibold mb-2">
                      Your Agent is Ready!
                    </h3>
                    <p className="text-sm text-muted-foreground mb-4">
                      Your AI agent will now start conversations with companies
                      to find your TOP 3 matches.
                    </p>
                  </div>
                  <Button
                    size="lg"
                    onClick={() => router.push("/dashboard/talent")}
                    className="bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700"
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
