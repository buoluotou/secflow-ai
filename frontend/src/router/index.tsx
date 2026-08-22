import { Navigate, createBrowserRouter } from 'react-router-dom'
import MainLayout from '../layouts/MainLayout'
import Login from '../pages/Login'
import Dashboard from '../pages/Dashboard'
import Projects from '../pages/Projects'
import Assets from '../pages/Assets'
import Events from '../pages/Events'
import Findings from '../pages/Findings'
import IOCs from '../pages/IOCs'
import Incidents from '../pages/Incidents'
import IncidentDetail from '../pages/IncidentDetail'
import Scans from '../pages/Scans'
import Analysis from '../pages/Analysis'
import Reports from '../pages/Reports'
import Audit from '../pages/Audit'
import Settings from '../pages/Settings'

export const router = createBrowserRouter([
  { path: '/login', element: <Login /> },
  {
    path: '/',
    element: <MainLayout />,
    children: [
      { index: true, element: <Navigate to="/dashboard" replace /> },
      { path: 'dashboard', element: <Dashboard /> },
      { path: 'projects', element: <Projects /> },
      { path: 'assets', element: <Assets /> },
      { path: 'events', element: <Events /> },
      { path: 'findings', element: <Findings /> },
      { path: 'iocs', element: <IOCs /> },
      { path: 'incidents', element: <Incidents /> },
      { path: 'incidents/:id', element: <IncidentDetail /> },
      { path: 'scans', element: <Scans /> },
      { path: 'analysis', element: <Analysis /> },
      { path: 'reports', element: <Reports /> },
      { path: 'audit', element: <Audit /> },
      { path: 'settings', element: <Settings /> },
    ],
  },
])
