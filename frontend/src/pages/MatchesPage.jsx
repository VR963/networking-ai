import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { matchingAPI } from '../services/api';

const MatchesPage = () => {
  const { user } = useAuth();
  const [matches, setMatches] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('all'); // all, pending, accepted, rejected

  useEffect(() => {
    fetchMatches();
  }, [filter]);

  const fetchMatches = async () => {
    try {
      setLoading(true);
      const response = await matchingAPI.getMatches(user.id);
      let matchesData = response.data || [];

      // Apply filter
      if (filter !== 'all') {
        matchesData = matchesData.filter((m) => m.status === filter);
      }

      setMatches(matchesData);
    } catch (error) {
      console.error('Error fetching matches:', error);
      // Mock data for demonstration
      setMatches([
        {
          id: 1,
          job_title: 'Senior React Developer',
          company_name: 'TechCorp Inc.',
          location: 'San Francisco, CA',
          score: 95,
          status: 'pending',
          description: 'Looking for an experienced React developer to join our growing team.',
          requirements: ['React', 'TypeScript', 'Node.js'],
          salary_range: '$120k - $160k',
          match_reasons: [
            'Strong React and TypeScript experience',
            'Previous work in similar company size',
            'Skills align perfectly with requirements',
          ],
        },
        {
          id: 2,
          job_title: 'Full Stack Engineer',
          company_name: 'StartupXYZ',
          location: 'Remote',
          score: 92,
          status: 'pending',
          description: 'Join our mission to revolutionize the industry with cutting-edge technology.',
          requirements: ['React', 'Python', 'AWS'],
          salary_range: '$110k - $150k',
          match_reasons: [
            'Full stack experience matches perfectly',
            'Remote work preference aligned',
            'Startup experience is a plus',
          ],
        },
        {
          id: 3,
          job_title: 'Frontend Team Lead',
          company_name: 'Enterprise Solutions Ltd',
          location: 'New York, NY',
          score: 88,
          status: 'pending',
          description: 'Lead a team of talented frontend developers building enterprise applications.',
          requirements: ['React', 'Leadership', 'Agile'],
          salary_range: '$140k - $180k',
          match_reasons: [
            'Leadership experience noted',
            'Technical skills are excellent fit',
            'Team management background',
          ],
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleAcceptMatch = async (matchId) => {
    try {
      await matchingAPI.acceptMatch(matchId);
      alert('Match accepted! The company will be notified.');
      fetchMatches();
    } catch (error) {
      console.error('Error accepting match:', error);
      alert('Failed to accept match. Please try again.');
    }
  };

  const handleRejectMatch = async (matchId) => {
    if (!window.confirm('Are you sure you want to reject this match?')) return;

    try {
      await matchingAPI.rejectMatch(matchId);
      fetchMatches();
    } catch (error) {
      console.error('Error rejecting match:', error);
      alert('Failed to reject match. Please try again.');
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading your matches...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Your Matches</h1>
        <p className="text-gray-600">
          AI-powered job matches based on your skills, experience, and preferences
        </p>
      </div>

      {/* Filters */}
      <div className="flex items-center space-x-2 mb-6 overflow-x-auto">
        {['all', 'pending', 'accepted', 'rejected'].map((status) => (
          <button
            key={status}
            onClick={() => setFilter(status)}
            className={`px-4 py-2 rounded-lg font-medium text-sm whitespace-nowrap ${
              filter === status
                ? 'bg-primary-600 text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            {status.charAt(0).toUpperCase() + status.slice(1)}
          </button>
        ))}
      </div>

      {/* Matches List */}
      {matches.length > 0 ? (
        <div className="space-y-6">
          {matches.map((match) => (
            <div key={match.id} className="card hover:shadow-lg transition-shadow">
              {/* Match Score Badge */}
              <div className="flex items-start justify-between mb-4">
                <div className="flex-1">
                  <div className="flex items-center space-x-3 mb-2">
                    <h2 className="text-2xl font-bold text-gray-900">{match.job_title}</h2>
                    <span className="px-3 py-1 bg-green-100 text-green-800 rounded-full text-sm font-semibold">
                      {match.score}% Match
                    </span>
                  </div>
                  <div className="flex items-center space-x-4 text-gray-600">
                    <span className="font-medium">{match.company_name}</span>
                    <span>•</span>
                    <span className="flex items-center">
                      <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
                      </svg>
                      {match.location}
                    </span>
                    <span>•</span>
                    <span className="text-primary-600 font-medium">{match.salary_range}</span>
                  </div>
                </div>
              </div>

              {/* Description */}
              <p className="text-gray-700 mb-4">{match.description}</p>

              {/* Requirements */}
              <div className="mb-4">
                <h3 className="text-sm font-semibold text-gray-900 mb-2">Key Requirements</h3>
                <div className="flex flex-wrap gap-2">
                  {match.requirements.map((req, idx) => (
                    <span
                      key={idx}
                      className="px-3 py-1 bg-blue-50 text-blue-700 rounded-full text-sm"
                    >
                      {req}
                    </span>
                  ))}
                </div>
              </div>

              {/* Match Reasons */}
              <div className="mb-6">
                <h3 className="text-sm font-semibold text-gray-900 mb-2">
                  Why this is a great match for you
                </h3>
                <ul className="space-y-2">
                  {match.match_reasons.map((reason, idx) => (
                    <li key={idx} className="flex items-start text-sm text-gray-600">
                      <svg className="w-5 h-5 text-green-500 mr-2 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                      {reason}
                    </li>
                  ))}
                </ul>
              </div>

              {/* Actions */}
              {match.status === 'pending' && (
                <div className="flex items-center space-x-3 pt-4 border-t border-gray-200">
                  <button
                    onClick={() => handleAcceptMatch(match.id)}
                    className="btn-primary flex-1"
                  >
                    <svg className="w-5 h-5 inline-block mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                    Accept Match
                  </button>
                  <button
                    onClick={() => handleRejectMatch(match.id)}
                    className="btn-secondary flex-1"
                  >
                    Not Interested
                  </button>
                  <button className="btn-secondary">
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                  </button>
                </div>
              )}

              {match.status === 'accepted' && (
                <div className="pt-4 border-t border-gray-200">
                  <div className="flex items-center justify-between">
                    <span className="text-green-600 font-medium flex items-center">
                      <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                      Match Accepted
                    </span>
                    <button className="btn-primary">Contact Company</button>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      ) : (
        <div className="card text-center py-12">
          <svg className="mx-auto h-16 w-16 text-gray-400 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <h3 className="text-lg font-medium text-gray-900 mb-2">No matches found</h3>
          <p className="text-gray-600 mb-6">
            {filter === 'all'
              ? "Our AI agents are working to find perfect matches for you. Check back soon!"
              : `No ${filter} matches at the moment.`}
          </p>
          <button
            onClick={() => setFilter('all')}
            className="btn-secondary"
          >
            View All Matches
          </button>
        </div>
      )}
    </div>
  );
};

export default MatchesPage;
