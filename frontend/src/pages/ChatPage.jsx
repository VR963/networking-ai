import React, { useState, useEffect, useRef } from 'react';
import { useAuth } from '../context/AuthContext';
import { agentAPI } from '../services/api';

const ChatPage = () => {
  const { user } = useAuth();
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [selectedAgent, setSelectedAgent] = useState('career-advisor');
  const messagesEndRef = useRef(null);

  const agents = [
    { id: 'career-advisor', name: 'Career Advisor', icon: '💼', description: 'Get personalized career guidance' },
    { id: 'job-matcher', name: 'Job Matcher', icon: '🎯', description: 'Find the perfect job matches' },
    { id: 'interview-coach', name: 'Interview Coach', icon: '🎓', description: 'Prepare for interviews' },
    { id: 'resume-expert', name: 'Resume Expert', icon: '📝', description: 'Optimize your resume' },
  ];

  useEffect(() => {
    // Load conversation history
    loadConversationHistory();
  }, [selectedAgent]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const loadConversationHistory = async () => {
    try {
      const response = await agentAPI.getConversationHistory(selectedAgent, user.id);
      if (response.data?.messages) {
        setMessages(response.data.messages);
      } else {
        // Welcome message for new conversations
        setMessages([
          {
            id: 'welcome',
            role: 'assistant',
            content: getWelcomeMessage(selectedAgent),
            timestamp: new Date(),
          },
        ]);
      }
    } catch (error) {
      console.error('Error loading conversation:', error);
      setMessages([
        {
          id: 'welcome',
          role: 'assistant',
          content: getWelcomeMessage(selectedAgent),
          timestamp: new Date(),
        },
      ]);
    }
  };

  const getWelcomeMessage = (agentId) => {
    const welcomeMessages = {
      'career-advisor': `Hello ${user?.name}! I'm your AI Career Advisor. I'm here to help you navigate your career journey, explore opportunities, and make informed decisions. How can I assist you today?`,
      'job-matcher': `Hi ${user?.name}! I'm the Job Matcher AI. I analyze your skills, experience, and preferences to find the perfect job opportunities for you. What kind of role are you interested in?`,
      'interview-coach': `Welcome ${user?.name}! I'm your Interview Coach. I'll help you prepare for interviews, practice common questions, and boost your confidence. Ready to get started?`,
      'resume-expert': `Hello ${user?.name}! I'm the Resume Expert AI. I can help you create, optimize, and tailor your resume to stand out to employers. What would you like to work on?`,
    };
    return welcomeMessages[agentId] || 'Hello! How can I help you today?';
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!inputMessage.trim() || loading) return;

    const userMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: inputMessage,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInputMessage('');
    setLoading(true);

    try {
      const response = await agentAPI.chatWithAgent(selectedAgent, inputMessage);
      const assistantMessage = {
        id: `assistant-${Date.now()}`,
        role: 'assistant',
        content: response.data.message || response.data.response,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error) {
      console.error('Error sending message:', error);
      const errorMessage = {
        id: `error-${Date.now()}`,
        role: 'assistant',
        content: 'Sorry, I encountered an error. Please try again.',
        timestamp: new Date(),
        isError: true,
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  const currentAgent = agents.find(a => a.id === selectedAgent);

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">AI Assistant</h1>
        <p className="text-gray-600">Chat with specialized AI agents to enhance your career journey</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Agent Selector Sidebar */}
        <div className="lg:col-span-1">
          <div className="card sticky top-4">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Select Agent</h2>
            <div className="space-y-2">
              {agents.map((agent) => (
                <button
                  key={agent.id}
                  onClick={() => setSelectedAgent(agent.id)}
                  className={`w-full text-left p-3 rounded-lg transition-colors ${
                    selectedAgent === agent.id
                      ? 'bg-primary-100 border-2 border-primary-500'
                      : 'bg-gray-50 hover:bg-gray-100 border-2 border-transparent'
                  }`}
                >
                  <div className="flex items-center space-x-3">
                    <span className="text-2xl">{agent.icon}</span>
                    <div className="flex-1">
                      <p className="font-medium text-gray-900 text-sm">{agent.name}</p>
                      <p className="text-xs text-gray-600">{agent.description}</p>
                    </div>
                  </div>
                </button>
              ))}
            </div>

            <div className="mt-6 pt-6 border-t border-gray-200">
              <h3 className="text-sm font-semibold text-gray-900 mb-2">Quick Tips</h3>
              <ul className="space-y-2 text-xs text-gray-600">
                <li>• Be specific with your questions</li>
                <li>• Share relevant details about your experience</li>
                <li>• Ask follow-up questions for clarity</li>
                <li>• Take notes on important advice</li>
              </ul>
            </div>
          </div>
        </div>

        {/* Chat Interface */}
        <div className="lg:col-span-3">
          <div className="card h-[calc(100vh-200px)] flex flex-col">
            {/* Chat Header */}
            <div className="flex items-center justify-between pb-4 border-b border-gray-200">
              <div className="flex items-center space-x-3">
                <div className="w-10 h-10 bg-primary-100 rounded-full flex items-center justify-center">
                  <span className="text-2xl">{currentAgent?.icon}</span>
                </div>
                <div>
                  <h3 className="font-semibold text-gray-900">{currentAgent?.name}</h3>
                  <p className="text-sm text-gray-600">{currentAgent?.description}</p>
                </div>
              </div>
              <div className="flex items-center space-x-2">
                <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                <span className="text-sm text-gray-600">Online</span>
              </div>
            </div>

            {/* Messages Container */}
            <div className="flex-1 overflow-y-auto py-4 space-y-4">
              {messages.map((message) => (
                <div
                  key={message.id}
                  className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <div className={`flex items-start space-x-2 max-w-[80%] ${
                    message.role === 'user' ? 'flex-row-reverse space-x-reverse' : ''
                  }`}>
                    {/* Avatar */}
                    <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
                      message.role === 'user'
                        ? 'bg-primary-600'
                        : 'bg-gray-200'
                    }`}>
                      {message.role === 'user' ? (
                        <span className="text-white text-sm font-medium">
                          {user?.name?.charAt(0).toUpperCase()}
                        </span>
                      ) : (
                        <span className="text-lg">{currentAgent?.icon}</span>
                      )}
                    </div>

                    {/* Message Bubble */}
                    <div className={`rounded-lg p-3 ${
                      message.role === 'user'
                        ? 'bg-primary-600 text-white'
                        : message.isError
                        ? 'bg-red-50 text-red-900'
                        : 'bg-gray-100 text-gray-900'
                    }`}>
                      <p className="text-sm whitespace-pre-wrap">{message.content}</p>
                      <p className={`text-xs mt-1 ${
                        message.role === 'user' ? 'text-primary-200' : 'text-gray-500'
                      }`}>
                        {new Date(message.timestamp).toLocaleTimeString([], {
                          hour: '2-digit',
                          minute: '2-digit',
                        })}
                      </p>
                    </div>
                  </div>
                </div>
              ))}

              {loading && (
                <div className="flex justify-start">
                  <div className="flex items-start space-x-2 max-w-[80%]">
                    <div className="w-8 h-8 bg-gray-200 rounded-full flex items-center justify-center">
                      <span className="text-lg">{currentAgent?.icon}</span>
                    </div>
                    <div className="bg-gray-100 rounded-lg p-3">
                      <div className="flex space-x-2">
                        <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                        <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                        <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>

            {/* Input Form */}
            <div className="pt-4 border-t border-gray-200">
              <form onSubmit={handleSendMessage} className="flex items-end space-x-2">
                <textarea
                  value={inputMessage}
                  onChange={(e) => setInputMessage(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault();
                      handleSendMessage(e);
                    }
                  }}
                  placeholder="Type your message... (Shift+Enter for new line)"
                  className="flex-1 input-field resize-none"
                  rows={2}
                  disabled={loading}
                />
                <button
                  type="submit"
                  disabled={loading || !inputMessage.trim()}
                  className="btn-primary px-6 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                  </svg>
                </button>
              </form>
              <p className="text-xs text-gray-500 mt-2">
                Press Enter to send, Shift+Enter for new line
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ChatPage;
