# Networking AI - Frontend

Modern React-based web application for the Networking AI platform, featuring AI-powered job matching and intelligent agent conversations.

## Features

- **Landing Page**: Overview of the platform with key features
- **Authentication**: Login and registration for job seekers and companies
- **Job Seeker Dashboard**: View matches, browse jobs, and track career progress
- **Company Dashboard**: Manage job postings, review candidates, and track hiring pipeline
- **AI Chat Interface**: Interactive chat with specialized AI agents (Career Advisor, Job Matcher, Interview Coach, Resume Expert)
- **Matches Page**: View and manage AI-powered job matches with detailed insights
- **Responsive Design**: Mobile-friendly interface with TailwindCSS

## Tech Stack

- **React 18**: Modern React with hooks
- **Vite**: Fast build tool and dev server
- **React Router**: Client-side routing
- **TailwindCSS**: Utility-first CSS framework
- **Axios**: HTTP client for API calls
- **Context API**: State management for authentication

## Prerequisites

- Node.js 18+ and npm
- Backend API running on `http://localhost:8000` (see main README)

## Installation

1. Install dependencies:
```bash
npm install
```

2. Configure environment variables:
```bash
cp .env.example .env
# Edit .env to set your API URL if different from default
```

3. Start the development server:
```bash
npm run dev
```

The app will be available at `http://localhost:5173`

## Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run preview` - Preview production build
- `npm run lint` - Run ESLint

## Project Structure

```
frontend/
├── src/
│   ├── components/       # Reusable components
│   │   └── Layout.jsx   # Main layout with navigation
│   ├── context/         # React context providers
│   │   └── AuthContext.jsx  # Authentication context
│   ├── pages/           # Page components
│   │   ├── LandingPage.jsx
│   │   ├── Login.jsx
│   │   ├── Register.jsx
│   │   ├── JobSeekerDashboard.jsx
│   │   ├── CompanyDashboard.jsx
│   │   ├── ChatPage.jsx
│   │   └── MatchesPage.jsx
│   ├── services/        # API service layer
│   │   └── api.js      # API client and endpoints
│   ├── App.jsx         # Main app with routing
│   ├── main.jsx        # Entry point
│   └── index.css       # Global styles
├── public/             # Static assets
├── .env               # Environment variables
├── tailwind.config.js # Tailwind configuration
├── vite.config.js     # Vite configuration
└── package.json       # Dependencies
```

## API Integration

The frontend connects to the backend API using Axios. All API calls are centralized in `src/services/api.js`:

- **Auth API**: Login, register, logout
- **User API**: Profile management, resume upload
- **Job API**: Browse jobs, search, CRUD operations
- **Matching API**: Get matches, accept/reject matches
- **Agent API**: Chat with AI agents, conversation history
- **Company API**: Manage company profile and candidates

## Authentication

The app uses JWT tokens stored in localStorage. The `AuthContext` provides:

- `user`: Current user object
- `login(email, password)`: Login function
- `register(userData)`: Registration function
- `logout()`: Logout function
- `isAuthenticated`: Boolean auth status
- `isJobSeeker`: Boolean for job seeker role
- `isCompany`: Boolean for company role

## Protected Routes

Routes are protected based on authentication status and user role:

- Public routes: `/`, `/login`, `/register`
- Job Seeker routes: `/dashboard`, `/matches`, `/jobs`
- Company routes: `/company-dashboard`, `/candidates`, `/post-job`
- Common protected routes: `/chat`, `/profile`

## Customization

### Changing API URL

Edit `.env` file:
```
VITE_API_URL=http://your-api-url.com/api/v1
```

### Styling

The app uses TailwindCSS. To customize:

1. Edit `tailwind.config.js` for theme customization
2. Modify `src/index.css` for global styles
3. Use Tailwind classes in components

### Adding New Pages

1. Create component in `src/pages/`
2. Add route in `src/App.jsx`
3. Add navigation link in `src/components/Layout.jsx`

## Deployment

### Build for Production

```bash
npm run build
```

This creates an optimized build in the `dist/` directory.

### Deploy to Vercel

```bash
npm install -g vercel
vercel
```

### Deploy to Netlify

```bash
npm install -g netlify-cli
netlify deploy --prod
```

### Docker Deployment

Build and run with Docker:

```bash
docker build -t networking-ai-frontend .
docker run -p 3000:80 networking-ai-frontend
```

## Testing

To test the application:

1. Start the backend API (see main README)
2. Start the frontend dev server: `npm run dev`
3. Visit `http://localhost:5173`
4. Register as a job seeker or company
5. Explore the various features

### Mock Data

If the backend API is not available, some pages will show mock data for demonstration purposes. This is useful for frontend development without requiring a running backend.

## Troubleshooting

### API Connection Issues

- Ensure backend is running on the correct port
- Check CORS configuration in backend
- Verify `VITE_API_URL` in `.env`

### Build Errors

- Clear node_modules: `rm -rf node_modules && npm install`
- Clear Vite cache: `rm -rf node_modules/.vite`

### Styling Issues

- Ensure Tailwind is properly configured
- Check that `index.css` imports Tailwind directives
- Rebuild: `npm run build`

## Contributing

1. Create a feature branch
2. Make your changes
3. Test thoroughly
4. Submit a pull request

## License

MIT License - see main project LICENSE file

## Support

For issues and questions, please refer to the main project repository or contact the development team.
