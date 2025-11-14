import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { companyAPI, jobAPI } from '../services/api';

const CompanyDashboard = () => {
  const { user } = useAuth();
  const [jobs, setJobs] = useState([]);
  const [candidates, setCandidates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState({
    activeJobs: 0,
    totalCandidates: 0,
    pendingReviews: 0,
    matchedCandidates: 0,
  });

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    try {
      setLoading(true);
      // Fetch company jobs and candidates
      const jobsRes = await companyAPI.getCompanyJobs(user.company_id).catch(() => ({ data: [] }));
      setJobs(jobsRes.data || []);

      // Calculate stats
      setStats({
        activeJobs: jobsRes.data?.filter(j => j.status === 'active').length || 0,
        totalCandidates: 45, // Mock data
        pendingReviews: 12,   // Mock data
        matchedCandidates: 8, // Mock data
      });
    } catch (error) {
      console.error('Error fetching dashboard data:', error);
    } finally {
      setLoading(false);
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
          Welcome, {user?.name}!
        </h1>
        <p className="text-gray-600">Manage your talent pipeline with AI-powered insights</p>
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
        <div className="card">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600 mb-1">Active Jobs</p>
              <p className="text-3xl font-bold text-primary-600">{stats.activeJobs}</p>
            </div>
            <div className="w-12 h-12 bg-primary-100 rounded-full flex items-center justify-center">
              <svg className="w-6 h-6 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 13.255A23.931 23.931 0 0112 15c-3.183 0-6.22-.62-9-1.745M16 6V4a2 2 0 00-2-2h-4a2 2 0 00-2 2v2m4 6h.01M5 20h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
              </svg>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600 mb-1">Total Candidates</p>
              <p className="text-3xl font-bold text-blue-600">{stats.totalCandidates}</p>
            </div>
            <div className="w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center">
              <svg className="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
              </svg>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600 mb-1">Pending Reviews</p>
              <p className="text-3xl font-bold text-yellow-600">{stats.pendingReviews}</p>
            </div>
            <div className="w-12 h-12 bg-yellow-100 rounded-full flex items-center justify-center">
              <svg className="w-6 h-6 text-yellow-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600 mb-1">AI Matches</p>
              <p className="text-3xl font-bold text-green-600">{stats.matchedCandidates}</p>
            </div>
            <div className="w-12 h-12 bg-green-100 rounded-full flex items-center justify-center">
              <svg className="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Main Content */}
        <div className="lg:col-span-2 space-y-6">
          {/* Active Job Postings */}
          <div className="card">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-semibold text-gray-900">Active Job Postings</h2>
              <Link to="/post-job" className="btn-primary text-sm">
                + Post New Job
              </Link>
            </div>
            {jobs.length > 0 ? (
              <div className="space-y-4">
                {jobs.slice(0, 5).map((job) => (
                  <div key={job.id} className="border border-gray-200 rounded-lg p-4 hover:border-primary-300 transition-colors">
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <h3 className="font-semibold text-gray-900">{job.title}</h3>
                        <div className="flex items-center mt-2 space-x-4 text-sm text-gray-500">
                          <span>{job.location}</span>
                          <span>•</span>
                          <span>{job.applications || 0} applications</span>
                          <span>•</span>
                          <span className={`px-2 py-1 rounded-full text-xs ${
                            job.status === 'active' ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
                          }`}>
                            {job.status}
                          </span>
                        </div>
                      </div>
                      <Link
                        to={`/jobs/${job.id}`}
                        className="btn-secondary text-sm"
                      >
                        Manage
                      </Link>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-8">
                <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 13.255A23.931 23.931 0 0112 15c-3.183 0-6.22-.62-9-1.745M16 6V4a2 2 0 00-2-2h-4a2 2 0 00-2 2v2m4 6h.01M5 20h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                </svg>
                <p className="mt-4 text-gray-600">No active job postings</p>
                <Link to="/post-job" className="btn-primary mt-4 inline-block">
                  Post Your First Job
                </Link>
              </div>
            )}
          </div>

          {/* AI-Matched Candidates */}
          <div className="card">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-semibold text-gray-900">AI-Matched Candidates</h2>
              <Link to="/candidates" className="text-primary-600 hover:text-primary-700 text-sm font-medium">
                View All →
              </Link>
            </div>
            <div className="space-y-4">
              {/* Mock candidates */}
              {[
                { id: 1, name: 'Sarah Johnson', role: 'Senior React Developer', match: 95, experience: '5 years' },
                { id: 2, name: 'Michael Chen', role: 'Full Stack Engineer', match: 92, experience: '7 years' },
                { id: 3, name: 'Emily Davis', role: 'Frontend Developer', match: 88, experience: '4 years' },
              ].map((candidate) => (
                <div key={candidate.id} className="border border-gray-200 rounded-lg p-4 hover:border-primary-300 transition-colors">
                  <div className="flex items-start justify-between">
                    <div className="flex items-start space-x-3 flex-1">
                      <div className="w-12 h-12 bg-primary-600 rounded-full flex items-center justify-center flex-shrink-0">
                        <span className="text-white font-medium">
                          {candidate.name.split(' ').map(n => n[0]).join('')}
                        </span>
                      </div>
                      <div>
                        <h3 className="font-semibold text-gray-900">{candidate.name}</h3>
                        <p className="text-sm text-gray-600 mt-1">{candidate.role}</p>
                        <div className="flex items-center mt-2 space-x-4 text-sm text-gray-500">
                          <span>{candidate.experience}</span>
                          <span>•</span>
                          <span className="text-green-600 font-medium">{candidate.match}% match</span>
                        </div>
                      </div>
                    </div>
                    <div className="flex space-x-2">
                      <button className="btn-secondary text-sm">View</button>
                      <button className="btn-primary text-sm">Contact</button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Quick Actions */}
          <div className="card">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Quick Actions</h3>
            <div className="space-y-2">
              <Link to="/post-job" className="block w-full btn-primary text-sm text-left">
                Post New Job
              </Link>
              <Link to="/candidates" className="block w-full btn-secondary text-sm text-left">
                Browse Candidates
              </Link>
              <Link to="/chat" className="block w-full btn-secondary text-sm text-left">
                Chat with AI Agent
              </Link>
              <Link to="/company/settings" className="block w-full btn-secondary text-sm text-left">
                Company Settings
              </Link>
            </div>
          </div>

          {/* AI Agent Status */}
          <div className="card bg-gradient-to-br from-purple-50 to-purple-100">
            <div className="flex items-center space-x-2 mb-3">
              <div className="w-3 h-3 bg-green-500 rounded-full animate-pulse"></div>
              <h3 className="text-lg font-semibold text-gray-900">AI Agent Active</h3>
            </div>
            <p className="text-sm text-gray-600 mb-4">
              Your AI recruiting agent is actively searching for qualified candidates and engaging with job seekers.
            </p>
            <Link to="/chat" className="text-purple-700 font-medium text-sm hover:text-purple-800">
              View Agent Activity →
            </Link>
          </div>

          {/* Hiring Insights */}
          <div className="card">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Hiring Insights</h3>
            <div className="space-y-3">
              <div className="flex items-start space-x-2">
                <div className="w-2 h-2 bg-primary-600 rounded-full mt-2 flex-shrink-0"></div>
                <p className="text-sm text-gray-600">
                  Your job postings receive 40% more applications than average
                </p>
              </div>
              <div className="flex items-start space-x-2">
                <div className="w-2 h-2 bg-primary-600 rounded-full mt-2 flex-shrink-0"></div>
                <p className="text-sm text-gray-600">
                  AI agents have identified 8 highly qualified candidates this week
                </p>
              </div>
              <div className="flex items-start space-x-2">
                <div className="w-2 h-2 bg-primary-600 rounded-full mt-2 flex-shrink-0"></div>
                <p className="text-sm text-gray-600">
                  Average time-to-hire: 18 days (32% faster than industry average)
                </p>
              </div>
            </div>
          </div>

          {/* Recruiting Tips */}
          <div className="card bg-gradient-to-br from-blue-50 to-blue-100">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">Pro Tip</h3>
            <p className="text-sm text-gray-600">
              Jobs with detailed requirements get 3x more qualified matches from our AI agents. Update your job descriptions for better results!
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default CompanyDashboard;
