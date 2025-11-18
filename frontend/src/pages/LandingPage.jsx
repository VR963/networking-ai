import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

const LandingPage = () => {
  const navigate = useNavigate();
  const { isAuthenticated, user } = useAuth();

  // If authenticated, redirect to dashboard
  React.useEffect(() => {
    if (isAuthenticated) {
      const dashboardPath = user?.role === 'job_seeker' ? '/dashboard' : '/company-dashboard';
      navigate(dashboardPath);
    }
  }, [isAuthenticated, user, navigate]);

  const handleRoleSelection = (role) => {
    navigate(`/register?role=${role}`);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50 flex items-center justify-center px-4 py-12">
      <div className="max-w-6xl w-full">
        {/* Header */}
        <div className="text-center mb-16">
          <h1 className="text-4xl md:text-6xl font-bold text-gray-900 mb-4">
            AI-Native Professional Networking
          </h1>
          <p className="text-xl md:text-2xl text-gray-600 mb-2">
            Let autonomous AI agents find your perfect career match
          </p>
          <p className="text-lg text-gray-500">
            Choose your path to get started
          </p>
        </div>

        {/* Split Circle */}
        <div className="flex items-center justify-center mb-12">
          <div className="relative w-full max-w-2xl aspect-square">
            {/* Circle Container */}
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="relative w-full h-full max-w-md max-h-md">
                {/* Talent Side (Left Half) */}
                <button
                  onClick={() => handleRoleSelection('job_seeker')}
                  className="absolute left-0 top-0 w-1/2 h-full overflow-hidden group cursor-pointer focus:outline-none focus:ring-4 focus:ring-primary-300 rounded-l-full transition-all"
                  aria-label="Register as Talent"
                >
                  <div className="absolute inset-0 bg-gradient-to-br from-primary-500 to-primary-700 group-hover:from-primary-600 group-hover:to-primary-800 transition-all duration-300 rounded-l-full flex items-center justify-center transform group-hover:scale-105 origin-right">
                    <div className="text-center pr-8 transform group-hover:translate-x-2 transition-transform duration-300">
                      {/* User Icon */}
                      <div className="mb-4 flex justify-center">
                        <svg className="w-16 h-16 md:w-20 md:h-20 text-white drop-shadow-lg" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                        </svg>
                      </div>
                      <h2 className="text-2xl md:text-3xl font-bold text-white mb-2 drop-shadow-md">
                        Talent
                      </h2>
                      <p className="text-sm md:text-base text-primary-100 font-medium">
                        Find Your Dream Job
                      </p>
                    </div>
                  </div>
                </button>

                {/* Hiring Manager Side (Right Half) */}
                <button
                  onClick={() => handleRoleSelection('company')}
                  className="absolute right-0 top-0 w-1/2 h-full overflow-hidden group cursor-pointer focus:outline-none focus:ring-4 focus:ring-indigo-300 rounded-r-full transition-all"
                  aria-label="Register as Hiring Manager"
                >
                  <div className="absolute inset-0 bg-gradient-to-bl from-indigo-500 to-indigo-700 group-hover:from-indigo-600 group-hover:to-indigo-800 transition-all duration-300 rounded-r-full flex items-center justify-center transform group-hover:scale-105 origin-left">
                    <div className="text-center pl-8 transform group-hover:translate-x-[-0.5rem] transition-transform duration-300">
                      {/* Briefcase Icon */}
                      <div className="mb-4 flex justify-center">
                        <svg className="w-16 h-16 md:w-20 md:h-20 text-white drop-shadow-lg" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 13.255A23.931 23.931 0 0112 15c-3.183 0-6.22-.62-9-1.745M16 6V4a2 2 0 00-2-2h-4a2 2 0 00-2 2v2m4 6h.01M5 20h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                        </svg>
                      </div>
                      <h2 className="text-2xl md:text-3xl font-bold text-white mb-2 drop-shadow-md">
                        Hiring Manager
                      </h2>
                      <p className="text-sm md:text-base text-indigo-100 font-medium">
                        Find Perfect Candidates
                      </p>
                    </div>
                  </div>
                </button>

                {/* Center Divider Line */}
                <div className="absolute left-1/2 top-0 w-1 h-full bg-white transform -translate-x-1/2 z-10 shadow-lg"></div>

                {/* Outer Circle Border */}
                <div className="absolute inset-0 rounded-full border-4 border-white shadow-2xl pointer-events-none"></div>
              </div>
            </div>
          </div>
        </div>

        {/* Bottom Text */}
        <div className="text-center">
          <p className="text-gray-600 mb-4">
            Already have an account?{' '}
            <button
              onClick={() => navigate('/login')}
              className="text-primary-600 hover:text-primary-700 font-semibold underline"
            >
              Sign In
            </button>
          </p>
          <p className="text-sm text-gray-500">
            From 100 candidates to 3 perfect matches through intelligent agent-to-agent conversations
          </p>
        </div>
      </div>
    </div>
  );
};

export default LandingPage;
