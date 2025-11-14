import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { matchingAPI, jobAPI, interviewAPI } from '../services/api';

const JobSeekerDashboard = () => {
  const { user } = useAuth();
  const [matches, setMatches] = useState([]);
  const [recentJobs, setRecentJobs] = useState([]);
  const [interviewStatus, setInterviewStatus] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    try {
      setLoading(true);
      // Fetch matches, jobs, and interview status
      const [matchesRes, jobsRes] = await Promise.all([
        matchingAPI.getMatches(user.id).catch(() => ({ data: [] })),
        jobAPI.getAllJobs({ limit: 5 }).catch(() => ({ data: [] })),
      ]);

      setMatches(matchesRes.data || []);
      setRecentJobs(jobsRes.data || []);
    } catch (error) {
      console.error('Error fetching dashboard data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleRequestMatching = async () => {
    try {
      await matchingAPI.requestMatching(user.id);
      alert('Matching request submitted! Our AI agents will start working on finding your perfect matches.');
      fetchDashboardData();
    } catch (error) {
      console.error('Error requesting matching:', error);
      alert('Failed to request matching. Please try again.');
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading your dashboard...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Welcome Section */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">
          Welcome back, {user?.name}!
        </h1>
        <p className="text-gray-600">Here's your career journey overview</p>
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
        <div className="card">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600 mb-1">Active Matches</p>
              <p className="text-3xl font-bold text-primary-600">{matches.length}</p>
            </div>
            <div className="w-12 h-12 bg-primary-100 rounded-full flex items-center justify-center">
              <svg className="w-6 h-6 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
              </svg>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600 mb-1">Profile Strength</p>
              <p className="text-3xl font-bold text-green-600">85%</p>
            </div>
            <div className="w-12 h-12 bg-green-100 rounded-full flex items-center justify-center">
              <svg className="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600 mb-1">New Opportunities</p>
              <p className="text-3xl font-bold text-blue-600">{recentJobs.length}</p>
            </div>
            <div className="w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center">
              <svg className="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 13.255A23.931 23.931 0 0112 15c-3.183 0-6.22-.62-9-1.745M16 6V4a2 2 0 00-2-2h-4a2 2 0 00-2 2v2m4 6h.01M5 20h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
              </svg>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600 mb-1">AI Conversations</p>
              <p className="text-3xl font-bold text-purple-600">12</p>
            </div>
            <div className="w-12 h-12 bg-purple-100 rounded-full flex items-center justify-center">
              <svg className="w-6 h-6 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
              </svg>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Main Content */}
        <div className="lg:col-span-2 space-y-6">
          {/* AI Matching Section */}
          <div className="card">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-semibold text-gray-900">AI Agent Matching</h2>
              <Link to="/chat" className="text-primary-600 hover:text-primary-700 text-sm font-medium">
                Chat with Agent →
              </Link>
            </div>
            <p className="text-gray-600 mb-4">
              Our AI agents are analyzing your profile and searching for perfect job matches. They'll engage in conversations with company agents to find opportunities that align with your goals.
            </p>
            <button
              onClick={handleRequestMatching}
              className="btn-primary"
            >
              Request New Matches
            </button>
          </div>

          {/* Recent Matches */}
          <div className="card">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-semibold text-gray-900">Recent Matches</h2>
              <Link to="/matches" className="text-primary-600 hover:text-primary-700 text-sm font-medium">
                View All →
              </Link>
            </div>
            {matches.length > 0 ? (
              <div className="space-y-4">
                {matches.slice(0, 3).map((match) => (
                  <div key={match.id} className="border border-gray-200 rounded-lg p-4 hover:border-primary-300 transition-colors">
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <h3 className="font-semibold text-gray-900">{match.job_title}</h3>
                        <p className="text-sm text-gray-600 mt-1">{match.company_name}</p>
                        <div className="flex items-center mt-2 space-x-4">
                          <span className="text-sm text-gray-500">Match: {match.score}%</span>
                          <span className="text-xs px-2 py-1 bg-green-100 text-green-800 rounded-full">
                            {match.status}
                          </span>
                        </div>
                      </div>
                      <Link
                        to={`/matches/${match.id}`}
                        className="btn-secondary text-sm"
                      >
                        View Details
                      </Link>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-8 text-gray-500">
                <p>No matches yet. Request matching to get started!</p>
              </div>
            )}
          </div>

          {/* Recent Job Opportunities */}
          <div className="card">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-semibold text-gray-900">Recommended Jobs</h2>
              <Link to="/jobs" className="text-primary-600 hover:text-primary-700 text-sm font-medium">
                Browse All →
              </Link>
            </div>
            {recentJobs.length > 0 ? (
              <div className="space-y-4">
                {recentJobs.map((job) => (
                  <div key={job.id} className="border border-gray-200 rounded-lg p-4 hover:border-primary-300 transition-colors">
                    <h3 className="font-semibold text-gray-900">{job.title}</h3>
                    <p className="text-sm text-gray-600 mt-1">{job.company}</p>
                    <div className="flex items-center mt-2 space-x-4 text-sm text-gray-500">
                      <span>{job.location}</span>
                      <span>•</span>
                      <span>{job.employment_type}</span>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-8 text-gray-500">
                <p>No job recommendations available yet.</p>
              </div>
            )}
          </div>
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Quick Actions */}
          <div className="card">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Quick Actions</h3>
            <div className="space-y-2">
              <Link to="/profile" className="block w-full btn-secondary text-sm text-left">
                Edit Profile
              </Link>
              <Link to="/chat" className="block w-full btn-secondary text-sm text-left">
                Chat with AI Agent
              </Link>
              <Link to="/matches" className="block w-full btn-secondary text-sm text-left">
                View All Matches
              </Link>
              <Link to="/jobs" className="block w-full btn-secondary text-sm text-left">
                Browse Jobs
              </Link>
            </div>
          </div>

          {/* Profile Completion */}
          <div className="card bg-gradient-to-br from-primary-50 to-primary-100">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">Complete Your Profile</h3>
            <p className="text-sm text-gray-600 mb-4">
              A complete profile gets 3x more matches!
            </p>
            <div className="w-full bg-gray-200 rounded-full h-2 mb-4">
              <div className="bg-primary-600 h-2 rounded-full" style={{ width: '85%' }}></div>
            </div>
            <Link to="/profile" className="text-primary-700 font-medium text-sm hover:text-primary-800">
              Complete Profile →
            </Link>
          </div>

          {/* Tips & Insights */}
          <div className="card">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">AI Insights</h3>
            <div className="space-y-3">
              <div className="flex items-start space-x-2">
                <div className="w-2 h-2 bg-primary-600 rounded-full mt-2 flex-shrink-0"></div>
                <p className="text-sm text-gray-600">
                  Your skills in React and TypeScript are in high demand
                </p>
              </div>
              <div className="flex items-start space-x-2">
                <div className="w-2 h-2 bg-primary-600 rounded-full mt-2 flex-shrink-0"></div>
                <p className="text-sm text-gray-600">
                  Companies are actively searching for your experience level
                </p>
              </div>
              <div className="flex items-start space-x-2">
                <div className="w-2 h-2 bg-primary-600 rounded-full mt-2 flex-shrink-0"></div>
                <p className="text-sm text-gray-600">
                  Consider updating your resume to highlight recent projects
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default JobSeekerDashboard;
