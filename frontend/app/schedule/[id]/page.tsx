"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ArrowLeft, Calendar, Clock, CheckCircle2, User, Building2 } from "lucide-react";
import { useRouter, useParams } from "next/navigation";

export default function ScheduleMeetingPage() {
  const router = useRouter();
  const params = useParams();
  const [selectedDate, setSelectedDate] = useState<string>("");
  const [selectedTime, setSelectedTime] = useState<string>("");
  const [notes, setNotes] = useState<string>("");
  const [scheduled, setScheduled] = useState(false);

  const availableDates = [
    { date: "2024-11-15", dayOfWeek: "Friday" },
    { date: "2024-11-18", dayOfWeek: "Monday" },
    { date: "2024-11-19", dayOfWeek: "Tuesday" },
    { date: "2024-11-20", dayOfWeek: "Wednesday" },
    { date: "2024-11-21", dayOfWeek: "Thursday" },
  ];

  const availableTimes = [
    "9:00 AM",
    "10:00 AM",
    "11:00 AM",
    "1:00 PM",
    "2:00 PM",
    "3:00 PM",
    "4:00 PM",
  ];

  const handleSchedule = () => {
    if (selectedDate && selectedTime) {
      setScheduled(true);
    }
  };

  if (scheduled) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50 flex items-center justify-center">
        <Card className="max-w-md w-full mx-4">
          <CardContent className="p-8 text-center space-y-6">
            <div className="w-20 h-20 bg-green-100 rounded-full flex items-center justify-center mx-auto">
              <CheckCircle2 className="h-10 w-10 text-green-600" />
            </div>
            <div>
              <h2 className="text-2xl font-bold mb-2">Meeting Scheduled!</h2>
              <p className="text-muted-foreground">
                Your meeting with TechCorp has been confirmed for {selectedDate} at {selectedTime}.
              </p>
            </div>
            <div className="p-4 bg-blue-50 rounded-lg text-left space-y-2">
              <div className="flex items-center gap-2 text-sm">
                <Calendar className="h-4 w-4 text-blue-600" />
                <span className="font-medium">{selectedDate}</span>
              </div>
              <div className="flex items-center gap-2 text-sm">
                <Clock className="h-4 w-4 text-blue-600" />
                <span className="font-medium">{selectedTime} PST</span>
              </div>
              <div className="flex items-center gap-2 text-sm">
                <Building2 className="h-4 w-4 text-blue-600" />
                <span className="font-medium">TechCorp - Senior Software Engineer</span>
              </div>
            </div>
            <p className="text-sm text-muted-foreground">
              You'll receive a calendar invite and video conference link via email.
            </p>
            <div className="flex gap-3">
              <Button
                variant="outline"
                className="flex-1"
                onClick={() => router.push("/dashboard/talent")}
              >
                Back to Dashboard
              </Button>
              <Button
                className="flex-1 bg-gradient-to-r from-blue-600 to-purple-600"
                onClick={() => router.push("/conversation/" + params.id)}
              >
                View Conversation
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50">
      {/* Header */}
      <header className="border-b bg-white/80 backdrop-blur-sm sticky top-0 z-10">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center gap-4">
            <Button variant="ghost" size="icon" onClick={() => router.back()}>
              <ArrowLeft className="h-5 w-5" />
            </Button>
            <div>
              <h1 className="text-xl font-bold">Schedule Meeting</h1>
              <p className="text-sm text-muted-foreground">
                TechCorp - Senior Software Engineer
              </p>
            </div>
          </div>
        </div>
      </header>

      <div className="container mx-auto px-4 py-8">
        <div className="max-w-4xl mx-auto space-y-6">
          {/* Meeting Info */}
          <Card className="border-2 border-blue-200">
            <CardHeader>
              <CardTitle>Meeting Details</CardTitle>
              <CardDescription>
                Based on your conversation, this meeting will cover:
              </CardDescription>
            </CardHeader>
            <CardContent>
              <ul className="space-y-2 text-sm">
                <li className="flex items-start gap-2">
                  <CheckCircle2 className="h-4 w-4 text-green-600 flex-shrink-0 mt-0.5" />
                  <span>Team structure and direct collaborators</span>
                </li>
                <li className="flex items-start gap-2">
                  <CheckCircle2 className="h-4 w-4 text-green-600 flex-shrink-0 mt-0.5" />
                  <span>Onboarding process for new engineers</span>
                </li>
                <li className="flex items-start gap-2">
                  <CheckCircle2 className="h-4 w-4 text-green-600 flex-shrink-0 mt-0.5" />
                  <span>Relocation package details</span>
                </li>
                <li className="flex items-start gap-2">
                  <CheckCircle2 className="h-4 w-4 text-green-600 flex-shrink-0 mt-0.5" />
                  <span>Day-to-day responsibilities and current projects</span>
                </li>
              </ul>
              <div className="mt-4 p-3 bg-blue-50 rounded-lg text-sm">
                <strong>Duration:</strong> 45 minutes via video call
              </div>
            </CardContent>
          </Card>

          {/* Date Selection */}
          <Card>
            <CardHeader>
              <CardTitle>Select a Date</CardTitle>
              <CardDescription>Choose from available dates</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
                {availableDates.map((dateOption) => (
                  <button
                    key={dateOption.date}
                    onClick={() => setSelectedDate(dateOption.date)}
                    className={`p-4 rounded-lg border-2 transition-all ${
                      selectedDate === dateOption.date
                        ? "border-blue-600 bg-blue-50"
                        : "border-gray-200 hover:border-blue-300"
                    }`}
                  >
                    <div className="text-xs text-muted-foreground mb-1">
                      {dateOption.dayOfWeek}
                    </div>
                    <div className="font-semibold">{dateOption.date}</div>
                  </button>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Time Selection */}
          {selectedDate && (
            <Card>
              <CardHeader>
                <CardTitle>Select a Time</CardTitle>
                <CardDescription>All times in Pacific Time (PST)</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-3 md:grid-cols-7 gap-3">
                  {availableTimes.map((time) => (
                    <button
                      key={time}
                      onClick={() => setSelectedTime(time)}
                      className={`p-3 rounded-lg border-2 transition-all ${
                        selectedTime === time
                          ? "border-blue-600 bg-blue-50"
                          : "border-gray-200 hover:border-blue-300"
                      }`}
                    >
                      <div className="text-sm font-semibold">{time}</div>
                    </button>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Additional Notes */}
          {selectedDate && selectedTime && (
            <Card>
              <CardHeader>
                <CardTitle>Additional Notes (Optional)</CardTitle>
                <CardDescription>
                  Any specific topics you'd like to discuss?
                </CardDescription>
              </CardHeader>
              <CardContent>
                <textarea
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder="E.g., I'd like to learn more about the team's current tech stack challenges..."
                  className="w-full min-h-[100px] p-3 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-600"
                />
              </CardContent>
            </Card>
          )}

          {/* Confirm Button */}
          {selectedDate && selectedTime && (
            <Card className="border-2 border-green-200 bg-gradient-to-r from-green-50 to-blue-50">
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="font-semibold mb-1">Ready to schedule?</h3>
                    <p className="text-sm text-muted-foreground">
                      Meeting on {selectedDate} at {selectedTime} PST
                    </p>
                  </div>
                  <Button
                    size="lg"
                    onClick={handleSchedule}
                    className="bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700"
                  >
                    <Calendar className="mr-2 h-5 w-5" />
                    Confirm Meeting
                  </Button>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
