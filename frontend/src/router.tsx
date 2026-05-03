import { createBrowserRouter, Navigate } from 'react-router-dom'
import { AuthGuard } from './components/layout/AuthGuard'
import { AppShell } from './components/layout/AppShell'
import { LoginPage } from './pages/LoginPage'
import { DashboardPage } from './pages/DashboardPage'
import { ExceptionQueuePage } from './pages/ExceptionQueuePage'
import { FinancialTruthPage } from './pages/FinancialTruthPage'
import { CashForecastPage } from './pages/CashForecastPage'
import { DecisionsPage } from './pages/DecisionsPage'
import { ESOPPage } from './pages/ESOPPage'
import { AgentsPage } from './pages/AgentsPage'
import { AdminPage } from './pages/AdminPage'

export const router = createBrowserRouter([
  {
    path: '/login',
    element: <LoginPage />,
  },
  {
    path: '/',
    element: <AuthGuard />,
    children: [
      {
        element: <AppShell />,
        children: [
          {
            index: true,
            element: <DashboardPage />,
          },
          {
            path: 'exceptions',
            element: <ExceptionQueuePage />,
          },
          {
            path: 'financial',
            element: <FinancialTruthPage />,
          },
          {
            path: 'cash',
            element: <CashForecastPage />,
          },
          {
            path: 'decisions',
            element: <DecisionsPage />,
          },
          {
            path: 'esop',
            element: <ESOPPage />,
          },
          {
            path: 'agents',
            element: <AgentsPage />,
          },
          {
            path: 'admin',
            element: <AdminPage />,
          },
        ],
      },
    ],
  },
  {
    path: '*',
    element: <Navigate to="/" replace />,
  },
])
