import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, NavLink, Navigate, useLocation } from 'react-router-dom';
import { 
  LayoutDashboard, 
  ShieldCheck, 
  CreditCard, 
  ScrollText, 
  History, 
  LineChart, 
  LogOut, 
  ChevronLeft, 
  ChevronRight, 
  Database,
  Radio,
  User,
  Layers
} from 'lucide-react';
import Dashboard from './pages/Dashboard';
import BillPayment from './pages/BillPayment';
import OneView from './pages/OneView';
import Transactions from './pages/Transactions';
import TelemetryDashboard from './pages/TelemetryDashboard';
import PlatformDemo from './pages/PlatformDemo';
import Login from './pages/Login';
import Unauthorized from './pages/Unauthorized';
import AdminProvisioning from './pages/AdminProvisioning';
import { ToastManager } from './components/ToastManager';
import { useAuthStore } from './state/authStore';
import { useToastStore } from './state/toastStore';

// Strict Route Guard Wrapper with Compliance Auditing
interface ProtectedRouteProps {
  allowedRoles: string[];
  children: React.ReactNode;
}

const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ allowedRoles, children }) => {
  const { role, username } = useAuthStore();
  const location = useLocation();

  useEffect(() => {
    if (!allowedRoles.includes(role)) {
      // Compliance logging of privilege violation
      const logMessage = `[SECURITY AUDIT - PRIVILEGE VIOLATION] User "${username}" with Role "${role}" attempted unauthorized navigation to path "${location.pathname}" - ACCESS DENIED.`;
      console.warn(logMessage);
      useToastStore.getState().addToast(
        'error', 
        `Privilege Violation: Role '${role}' lacks clearance for this section.`
      );
    }
  }, [role, username, location, allowedRoles]);

  if (!allowedRoles.includes(role)) {
    return <Navigate to="/unauthorized" replace />;
  }

  return <>{children}</>;
};

export const App: React.FC = () => {
  const { role, jwtToken, username, logout } = useAuthStore();
  const [collapsed, setCollapsed] = useState(false);

  if (!jwtToken) {
    return (
      <Router>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="*" element={<Navigate to="/login" replace />} />
        </Routes>
        <ToastManager />
      </Router>
    );
  }

  const toggleSidebar = () => {
    setCollapsed(!collapsed);
  };

  const getRoleColor = (userRole: string) => {
    switch (userRole) {
      case 'ADMIN':
        return 'text-cyan-400 bg-cyan-950/40 border border-cyan-800/40';
      case 'OPERATIONS':
        return 'text-amber-400 bg-amber-950/40 border border-amber-800/40';
      case 'AUDITOR':
        return 'text-purple-400 bg-purple-950/40 border border-purple-800/40';
      default:
        return 'text-emerald-400 bg-emerald-950/40 border border-emerald-800/40';
    }
  };

  // Dynamic Sidebar menu schema based on role
  const menuItems = [
    { 
      path: '/', 
      label: 'Dashboard', 
      icon: <LayoutDashboard size={18} />, 
      roles: ['ADMIN', 'OPERATIONS', 'CLIENT', 'AUDITOR'] 
    },
    { 
      path: '/admin', 
      label: 'Admin Panel', 
      icon: <User size={18} />, 
      roles: ['ADMIN'] 
    },
    { 
      path: '/demo', 
      label: 'Security Operations', 
      icon: <ShieldCheck size={18} />, 
      roles: ['ADMIN'] 
    },
    { 
      path: '/payment', 
      label: 'Bill Payment', 
      icon: <CreditCard size={18} />, 
      roles: ['ADMIN', 'CLIENT', 'OPERATIONS'] 
    },
    { 
      path: '/oneview', 
      label: 'OneView Logs', 
      icon: <History size={18} />, 
      roles: ['ADMIN', 'CLIENT', 'OPERATIONS', 'AUDITOR'] 
    },
    { 
      path: '/transactions', 
      label: 'Audit Ledger', 
      icon: <ScrollText size={18} />, 
      roles: ['ADMIN', 'OPERATIONS', 'AUDITOR'] 
    },
    { 
      path: '/telemetry', 
      label: 'Telemetry Stats', 
      icon: <LineChart size={18} />, 
      roles: ['ADMIN'] 
    },
  ];

  // Filters navigation items user is permitted to see
  const visibleMenuItems = menuItems.filter(item => item.roles.includes(role));

  return (
    <Router>
      <div className="app-layout font-sans bg-[#030303] text-zinc-400 min-h-screen">
        {/* Sidebar Dock */}
        <aside className={`sidebar-premium ${collapsed ? 'sidebar-collapsed' : 'sidebar-expanded'} font-sans relative`}>
          {/* Collapse Toggle Trigger */}
          <button 
            onClick={toggleSidebar} 
            className="absolute top-4 -right-3 bg-[#0a0a0c] border border-zinc-800 text-zinc-400 hover:text-zinc-200 p-1 rounded-full cursor-pointer z-50 transition-colors"
          >
            {collapsed ? <ChevronRight size={13} /> : <ChevronLeft size={13} />}
          </button>

          {/* Sidebar Brand Header */}
          <div className="h-16 border-b border-zinc-900/60 flex items-center px-5 gap-3 overflow-hidden select-none">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-cyan-600 to-emerald-500 flex items-center justify-center shadow-lg shadow-cyan-950/40 flex-shrink-0">
              <Layers size={16} className="text-black stroke-[2.5]" />
            </div>
            {!collapsed && (
              <div className="flex flex-col">
                <span className="font-extrabold text-sm text-zinc-100 tracking-wider font-display">BBPS NEXTGEN</span>
                <span className="text-[9px] text-zinc-555 font-mono leading-none tracking-widest mt-0.5 font-bold text-cyan-500">RBAC ISOLATION</span>
              </div>
            )}
          </div>

          {/* Navigation Links */}
          <nav className="flex-1 px-3 py-4 space-y-1.5 overflow-y-auto">
            {visibleMenuItems.map((item) => (
              <NavLink
                key={item.path}
                to={item.path}
                className={({ isActive }) => `sidebar-link-premium p-2.5 gap-3 ${isActive ? 'active text-zinc-100' : 'text-zinc-400'}`}
                end={item.path === '/'}
              >
                {item.icon}
                {!collapsed && <span>{item.label}</span>}
              </NavLink>
            ))}
          </nav>

          {/* System Properties Footer */}
          {!collapsed && (
            <div className="p-4 border-t border-zinc-900/60 bg-zinc-950/40 text-[10px] font-mono text-zinc-500 flex flex-col space-y-1.5 rounded-t-lg mx-2 mb-2">
              <div className="flex items-center gap-1.5">
                <Database size={10} className="text-zinc-500" />
                <span>USER: {username}</span>
              </div>
              <div className="flex items-center gap-1.5">
                <Radio size={10} className="text-zinc-500" />
                <span>RBAC LEVEL: {role}</span>
              </div>
              <div className="text-[9px] text-zinc-600 mt-1 border-t border-zinc-900/40 pt-1">
                <span>SESSION STATUS: SECURED</span>
              </div>
            </div>
          )}
        </aside>

        {/* Main Panel Content */}
        <main className="main-content-premium">
          {/* Top Navbar */}
          <header className="top-nav-premium px-6 flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
              </span>
              <span className="font-mono text-xs text-zinc-500">
                COU SYSTEM ROUTER: <span className="text-emerald-500 font-bold">ONLINE</span>
              </span>
            </div>

            <div className="flex items-center space-x-5 text-xs font-mono">
              <div className="flex items-center space-x-2">
                <User size={13} className="text-zinc-500" />
                <span className="text-zinc-500">Active Role:</span>
                <span className={`px-2.5 py-0.5 text-[10px] font-bold rounded ${getRoleColor(role || '')}`}>
                  {role}
                </span>
              </div>
              
              <button
                onClick={() => logout()}
                className="flex items-center gap-1.5 bg-zinc-900/60 hover:bg-zinc-800 border border-zinc-800 text-zinc-300 py-1.5 px-3 rounded-lg text-[11px] font-semibold transition-all cursor-pointer"
              >
                <LogOut size={12} className="stroke-[2]" />
                <span>Logout</span>
              </button>
            </div>
          </header>

          {/* Subpage Router View */}
          <div className="page-container-premium">
            <Routes>
              {/* Common dashboard entry */}
              <Route path="/" element={<Dashboard />} />

              {/* Protected ADMIN routes */}
              <Route 
                path="/admin" 
                element={
                  <ProtectedRoute allowedRoles={['ADMIN']}>
                    <AdminProvisioning />
                  </ProtectedRoute>
                } 
              />
              <Route 
                path="/telemetry" 
                element={
                  <ProtectedRoute allowedRoles={['ADMIN']}>
                    <TelemetryDashboard />
                  </ProtectedRoute>
                } 
              />
              <Route 
                path="/metrics" 
                element={
                  <ProtectedRoute allowedRoles={['ADMIN']}>
                    <TelemetryDashboard />
                  </ProtectedRoute>
                } 
              />

              {/* Protected OPERATIONS/CLIENT routes */}
              <Route 
                path="/payments" 
                element={
                  <ProtectedRoute allowedRoles={['ADMIN', 'CLIENT', 'OPERATIONS']}>
                    <BillPayment />
                  </ProtectedRoute>
                } 
              />
              <Route 
                path="/bill-operations" 
                element={
                  <ProtectedRoute allowedRoles={['ADMIN', 'CLIENT', 'OPERATIONS']}>
                    <BillPayment />
                  </ProtectedRoute>
                } 
              />
              <Route 
                path="/payment" 
                element={
                  <ProtectedRoute allowedRoles={['ADMIN', 'CLIENT', 'OPERATIONS']}>
                    <BillPayment />
                  </ProtectedRoute>
                } 
              />
              <Route 
                path="/reconciliation" 
                element={
                  <ProtectedRoute allowedRoles={['ADMIN', 'OPERATIONS', 'AUDITOR']}>
                    <Transactions />
                  </ProtectedRoute>
                } 
              />
              <Route 
                path="/transactions" 
                element={
                  <ProtectedRoute allowedRoles={['ADMIN', 'OPERATIONS', 'AUDITOR']}>
                    <Transactions />
                  </ProtectedRoute>
                } 
              />

              {/* Protected Security routes */}
              <Route 
                path="/security" 
                element={
                  <ProtectedRoute allowedRoles={['ADMIN']}>
                    <PlatformDemo />
                  </ProtectedRoute>
                } 
              />
              <Route 
                path="/threat-center" 
                element={
                  <ProtectedRoute allowedRoles={['ADMIN']}>
                    <PlatformDemo />
                  </ProtectedRoute>
                } 
              />
              <Route 
                path="/replay-monitor" 
                element={
                  <ProtectedRoute allowedRoles={['ADMIN']}>
                    <PlatformDemo />
                  </ProtectedRoute>
                } 
              />
              <Route 
                path="/audit-logs" 
                element={
                  <ProtectedRoute allowedRoles={['ADMIN']}>
                    <PlatformDemo />
                  </ProtectedRoute>
                } 
              />
              <Route 
                path="/demo" 
                element={
                  <ProtectedRoute allowedRoles={['ADMIN']}>
                    <PlatformDemo />
                  </ProtectedRoute>
                } 
              />

              {/* Protected OneView routes */}
              <Route 
                path="/oneview" 
                element={
                  <ProtectedRoute allowedRoles={['ADMIN', 'CLIENT', 'OPERATIONS', 'AUDITOR']}>
                    <OneView />
                  </ProtectedRoute>
                } 
              />
              <Route 
                path="/customer-lookup" 
                element={
                  <ProtectedRoute allowedRoles={['ADMIN', 'CLIENT', 'OPERATIONS', 'AUDITOR']}>
                    <OneView />
                  </ProtectedRoute>
                } 
              />
              <Route 
                path="/bill-status" 
                element={
                  <ProtectedRoute allowedRoles={['ADMIN', 'CLIENT', 'OPERATIONS', 'AUDITOR']}>
                    <OneView />
                  </ProtectedRoute>
                } 
              />

              {/* Unauthorized Page */}
              <Route path="/unauthorized" element={<Unauthorized />} />

              {/* Fallback */}
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </div>
        </main>
      </div>
      <ToastManager />
    </Router>
  );
};

export default App;
