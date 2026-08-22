import { Navigate, createBrowserRouter } from 'react-router-dom'
import MainLayout from '../layouts/MainLayout'
import Login from '../pages/Login'
import Dashboard from '../pages/Dashboard'
import Incidents from '../pages/Incidents'
import IncidentDetail from '../pages/IncidentDetail'
import Findings from '../pages/Findings'
import Scans from '../pages/Scans'
import Reports from '../pages/Reports'
import Settings from '../pages/Settings'

// 精简导航：核心工作流 6 页（其余功能已合并到各页内）
export const router = createBrowserRouter([
  { path: '/login', element: <Login /> },
  {
    path: '/',
    element: <MainLayout />,
    children: [
      { index: true, element: <Navigate to="/dashboard" replace /> },
      { path: 'dashboard', element: <Dashboard /> },
      { path: 'incidents', element: <Incidents /> },
      { path: 'incidents/:id', element: <IncidentDetail /> },
      { path: 'findings', element: <Findings /> },
      { path: 'scans', element: <Scans /> },
      { path: 'reports', element: <Reports /> },
      { path: 'settings', element: <Settings /> },
    ],
  },
])
