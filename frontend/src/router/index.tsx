import { Navigate, createBrowserRouter } from 'react-router-dom'
import MainLayout from '../layouts/MainLayout'
import Login from '../pages/Login'
import Dashboard from '../pages/Dashboard'
import Incidents from '../pages/Incidents'
import IncidentDetail from '../pages/IncidentDetail'
import Findings from '../pages/Findings'
import Reports from '../pages/Reports'
import Audit from '../pages/Audit'
import Maintenance from '../pages/Maintenance'

// 安服大模块导航（6 模块）
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
      { path: 'reports', element: <Reports /> },
      { path: 'audit', element: <Audit /> },
      { path: 'maintenance', element: <Maintenance /> },
    ],
  },
])
