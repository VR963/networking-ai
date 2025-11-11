"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Sparkles, Upload, FileText, Link as LinkIcon, Loader2, CheckCircle2 } from "lucide-react";
import { useRouter } from "next/navigation";

type UploadStatus = "idle" | "uploading" | "analyzing" | "complete";

export default function DocumentUploadPage() {
  const router = useRouter();
  const [status, setStatus] = useState<UploadStatus>("idle");
  const [progress, setProgress] = useState(0);
  const [linkedinUrl, setLinkedinUrl] = useState("");
  const [personalWebsite, setPersonalWebsite] = useState("");
  const [githubUrl, setGithubUrl] = useState("");
  const [portfolioUrl, setPortfolioUrl] = useState("");
  const [resumeFile, setResumeFile] = useState<File | null>(null);
  const [certificatesFiles, setCertificatesFiles] = useState<File[]>([]);

  const handleResumeUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setResumeFile(e.target.files[0]);
    }
  };

  const handleCertificatesUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      setCertificatesFiles(Array.from(e.target.files));
    }
  };

  const handleAnalyze = async () => {
    setStatus("uploading");
    setProgress(0);

    // Simulate upload progress
    const uploadInterval = setInterval(() => {
      setProgress(prev => {
        if (prev >= 40) {
          clearInterval(uploadInterval);
          setStatus("analyzing");
          startAnalysis();
          return 40;
        }
        return prev + 10;
      });
    }, 300);
  };

  const startAnalysis = () => {
    // Simulate AI analysis progress
    const analysisInterval = setInterval(() => {
      setProgress(prev => {
        if (prev >= 100) {
          clearInterval(analysisInterval);
          setStatus("complete");
          return 100;
        }
        return prev + 5;
      });
    }, 400);
  };

  const handleContinue = () => {
    // Navigate to 6 questions onboarding
    router.push('/onboarding/questions');
  };

  const hasAnyData = linkedinUrl || personalWebsite || githubUrl || portfolioUrl || resumeFile || certificatesFiles.length > 0;

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50">
      {/* Header */}
      <header className="border-b bg-white/80 backdrop-blur-sm">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center gap-2">
            <Sparkles className="h-8 w-8 text-blue-600" />
            <h1 className="text-2xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
              Nexus AI
            </h1>
          </div>
        </div>
      </header>

      <div className="container mx-auto px-4 py-12">
        <div className="max-w-4xl mx-auto">
          {/* Title */}
          <div className="text-center mb-8">
            <h2 className="text-3xl font-bold mb-3">Tell Us About Yourself</h2>
            <p className="text-muted-foreground text-lg">
              Upload your documents and profiles so AI can understand you better.
              The more you share, the better your matches will be.
            </p>
          </div>

          {/* Upload Form */}
          {status === "idle" && (
            <Card>
              <CardHeader>
                <CardTitle>Upload Your Information</CardTitle>
                <CardDescription>
                  All data is stored securely in your private encrypted vault. Only you have access.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                {/* Resume Upload */}
                <div className="space-y-2">
                  <Label htmlFor="resume" className="flex items-center gap-2">
                    <FileText className="h-4 w-4" />
                    Resume / CV
                  </Label>
                  <div className="flex items-center gap-4">
                    <Input
                      id="resume"
                      type="file"
                      accept=".pdf,.doc,.docx"
                      onChange={handleResumeUpload}
                      className="cursor-pointer"
                    />
                    {resumeFile && (
                      <span className="text-sm text-green-600 flex items-center gap-1">
                        <CheckCircle2 className="h-4 w-4" />
                        {resumeFile.name}
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-muted-foreground">PDF, DOC, or DOCX format</p>
                </div>

                {/* LinkedIn URL */}
                <div className="space-y-2">
                  <Label htmlFor="linkedin" className="flex items-center gap-2">
                    <LinkIcon className="h-4 w-4" />
                    LinkedIn Profile URL
                  </Label>
                  <Input
                    id="linkedin"
                    type="url"
                    placeholder="https://linkedin.com/in/yourprofile"
                    value={linkedinUrl}
                    onChange={(e) => setLinkedinUrl(e.target.value)}
                  />
                </div>

                {/* Personal Website */}
                <div className="space-y-2">
                  <Label htmlFor="website" className="flex items-center gap-2">
                    <LinkIcon className="h-4 w-4" />
                    Personal Website (Optional)
                  </Label>
                  <Input
                    id="website"
                    type="url"
                    placeholder="https://yourwebsite.com"
                    value={personalWebsite}
                    onChange={(e) => setPersonalWebsite(e.target.value)}
                  />
                </div>

                {/* GitHub */}
                <div className="space-y-2">
                  <Label htmlFor="github" className="flex items-center gap-2">
                    <LinkIcon className="h-4 w-4" />
                    GitHub Profile (Optional)
                  </Label>
                  <Input
                    id="github"
                    type="url"
                    placeholder="https://github.com/yourusername"
                    value={githubUrl}
                    onChange={(e) => setGithubUrl(e.target.value)}
                  />
                </div>

                {/* Portfolio */}
                <div className="space-y-2">
                  <Label htmlFor="portfolio" className="flex items-center gap-2">
                    <LinkIcon className="h-4 w-4" />
                    Portfolio Link (Optional)
                  </Label>
                  <Input
                    id="portfolio"
                    type="url"
                    placeholder="https://yourportfolio.com"
                    value={portfolioUrl}
                    onChange={(e) => setPortfolioUrl(e.target.value)}
                  />
                </div>

                {/* Certificates */}
                <div className="space-y-2">
                  <Label htmlFor="certificates" className="flex items-center gap-2">
                    <Upload className="h-4 w-4" />
                    Certifications (Optional)
                  </Label>
                  <Input
                    id="certificates"
                    type="file"
                    accept=".pdf,.jpg,.jpeg,.png"
                    multiple
                    onChange={handleCertificatesUpload}
                    className="cursor-pointer"
                  />
                  {certificatesFiles.length > 0 && (
                    <div className="text-sm text-green-600 flex items-center gap-1">
                      <CheckCircle2 className="h-4 w-4" />
                      {certificatesFiles.length} file(s) selected
                    </div>
                  )}
                  <p className="text-xs text-muted-foreground">PDF, JPG, or PNG format</p>
                </div>

                <Button
                  size="lg"
                  className="w-full bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700"
                  onClick={handleAnalyze}
                  disabled={!hasAnyData}
                >
                  <Sparkles className="mr-2 h-5 w-5" />
                  Let AI Analyze My Profile
                </Button>

                {!hasAnyData && (
                  <p className="text-sm text-center text-muted-foreground">
                    Please upload at least one document or provide a URL to continue
                  </p>
                )}
              </CardContent>
            </Card>
          )}

          {/* Analysis Progress */}
          {(status === "uploading" || status === "analyzing") && (
            <Card>
              <CardContent className="p-12 text-center space-y-6">
                <div className="flex justify-center">
                  <Loader2 className="h-16 w-16 text-blue-600 animate-spin" />
                </div>
                <div>
                  <h3 className="text-2xl font-bold mb-2">
                    {status === "uploading" ? "Uploading Your Documents..." : "AI is Analyzing Your Profile..."}
                  </h3>
                  <p className="text-muted-foreground">
                    {status === "uploading"
                      ? "Securely transferring to your private vault"
                      : "Extracting skills, experience, and building your knowledge base"}
                  </p>
                </div>

                {/* Progress Bar */}
                <div className="max-w-md mx-auto">
                  <div className="w-full bg-gray-200 rounded-full h-3">
                    <div
                      className="bg-gradient-to-r from-blue-600 to-purple-600 h-3 rounded-full transition-all duration-300"
                      style={{ width: `${progress}%` }}
                    />
                  </div>
                  <p className="text-sm text-muted-foreground mt-2">{progress}% complete</p>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Complete */}
          {status === "complete" && (
            <Card>
              <CardContent className="p-12 text-center space-y-6">
                <div className="flex justify-center">
                  <div className="h-16 w-16 bg-green-100 rounded-full flex items-center justify-center">
                    <CheckCircle2 className="h-10 w-10 text-green-600" />
                  </div>
                </div>
                <div>
                  <h3 className="text-2xl font-bold mb-2">Profile Analysis Complete!</h3>
                  <p className="text-muted-foreground">
                    Your information has been securely stored and analyzed.
                    Now let's ask you 6 questions to understand your goals better.
                  </p>
                </div>

                <Button
                  size="lg"
                  className="bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700"
                  onClick={handleContinue}
                >
                  Continue to Questions
                </Button>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
