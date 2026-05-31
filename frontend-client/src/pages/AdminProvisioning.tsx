import React, { useEffect, useState } from 'react';
import { 
  UserPlus, 
  UserCheck, 
  UserX, 
  KeyRound, 
  RotateCw, 
  Sliders, 
  Info,
  ShieldAlert,
  Mail,
  User,
  ShieldCheck,
  CheckCircle,
  Eye,
  EyeOff,
  Globe,
  Activity,
  Plus,
  Trash2,
  Lock,
  Unlock,
  AlertCircle,
  FileText,
  Clock
} from 'lucide-react';
import apiClient from '../api/apiClient';
import { useToastStore } from '../state/toastStore';

interface UserItem {
  id: string;
  username: string;
  email: string;
  role: string;
  is_active: boolean;
}

interface IPWhitelistItem {
  id: string;
  ip_address: string;
  description: string;
  added_by: string;
  created_at: string;
}

interface RequestLogItem {
  id: string;
  request_id: string;
  timestamp: string;
  client_user: string;
  source_ip: string;
  endpoint: string;
  request_status: string;
  response_code: number;
  processing_time_ms: number;
}

interface SecurityEventItem {
  id: string;
  timestamp: string;
  username: string;
  role: string;
  action: string;
  details: string;
  ip_address: string;
}

interface SecurityStats {
  active_users: number;
  active_ips: number;
  failed_login_count: number;
  blocked_ip_count: number;
  active_sessions: number;
  api_usage_statistics: Record<string, number>;
  recent_events: SecurityEventItem[];
}

export const AdminProvisioning: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'users' | 'whitelist' | 'requests' | 'security'>('users');
  const [users, setUsers] = useState<UserItem[]>([]);
  const [loadingUsers, setLoadingUsers] = useState(false);

  // Form states for user creation
  const [newUsername, setNewUsername] = useState('');
  const [newEmail, setNewEmail] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [newRole, setNewRole] = useState('CLIENT');
  const [creating, setCreating] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  // Password reset states
  const [resetTargetUser, setResetTargetUser] = useState<string | null>(null);
  const [resetPasswordVal, setResetPasswordVal] = useState('');
  const [resetting, setResetting] = useState(false);

  // Modal for displaying newly generated secret admin key
  const [generatedKey, setGeneratedKey] = useState<string | null>(null);
  const [generatedUser, setGeneratedUser] = useState<string | null>(null);

  // Whitelist states
  const [whitelist, setWhitelist] = useState<IPWhitelistItem[]>([]);
  const [loadingWhitelist, setLoadingWhitelist] = useState(false);
  const [newIpAddress, setNewIpAddress] = useState('');
  const [newIpDesc, setNewIpDesc] = useState('');
  const [addingIp, setAddingIp] = useState(false);

  // Request logs states
  const [requestLogs, setRequestLogs] = useState<RequestLogItem[]>([]);
  const [loadingRequests, setLoadingRequests] = useState(false);
  const [logPage, setLogPage] = useState(0);
  const logLimit = 20;

  // Security dashboard stats states
  const [securityStats, setSecurityStats] = useState<SecurityStats | null>(null);
  const [loadingStats, setLoadingStats] = useState(false);

  const { addToast } = useToastStore();

  // Fetch Users
  const fetchUsers = async () => {
    setLoadingUsers(true);
    try {
      const response = await apiClient.get('/auth/users');
      const parsedData = typeof response.data === 'string' ? JSON.parse(response.data) : response.data;
      setUsers(parsedData);
    } catch (err: any) {
      addToast('error', `Failed to load users: ${err.message}`);
    } finally {
      setLoadingUsers(false);
    }
  };

  // Fetch Whitelist
  const fetchWhitelist = async () => {
    setLoadingWhitelist(true);
    try {
      const response = await apiClient.get('/security/ip-whitelist');
      const parsedData = typeof response.data === 'string' ? JSON.parse(response.data) : response.data;
      setWhitelist(parsedData);
    } catch (err: any) {
      addToast('error', `Failed to load IP whitelist: ${err.message}`);
    } finally {
      setLoadingWhitelist(false);
    }
  };

  // Fetch Request Logs
  const fetchRequestLogs = async () => {
    setLoadingRequests(true);
    try {
      const response = await apiClient.get(`/security/request-logs?skip=${logPage * logLimit}&limit=${logLimit}`);
      const parsedData = typeof response.data === 'string' ? JSON.parse(response.data) : response.data;
      setRequestLogs(parsedData);
    } catch (err: any) {
      addToast('error', `Failed to load request monitoring logs: ${err.message}`);
    } finally {
      setLoadingRequests(false);
    }
  };

  useEffect(() => {
    if (activeTab === 'requests') {
      fetchRequestLogs();
    }
  }, [activeTab, logPage]);

  // Fetch Security Stats
  const fetchSecurityStats = async () => {
    setLoadingStats(true);
    try {
      const response = await apiClient.get('/security/security-stats');
      const parsedData = typeof response.data === 'string' ? JSON.parse(response.data) : response.data;
      setSecurityStats(parsedData);
    } catch (err: any) {
      addToast('error', `Failed to load security statistics: ${err.message}`);
    } finally {
      setLoadingStats(false);
    }
  };

  useEffect(() => {
    if (activeTab === 'users') fetchUsers();
    else if (activeTab === 'whitelist') fetchWhitelist();
    else if (activeTab === 'requests') fetchRequestLogs();
    else if (activeTab === 'security') fetchSecurityStats();
  }, [activeTab]);

  // User Provisioning Actions
  const handleCreateUser = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newUsername.trim() || !newEmail.trim()) {
      addToast('error', 'Please fill in all provisioning fields.');
      return;
    }
    if (newRole === 'CLIENT' && !newPassword) {
      addToast('error', 'Password is required to provision a Client account.');
      return;
    }

    setCreating(true);
    try {
      if (newRole === 'CLIENT') {
        await apiClient.post('/auth/register-client', {
          username: newUsername.trim(),
          email: newEmail.trim(),
          password: newPassword,
          organization: null,
          company: null
        });
        addToast('success', `Successfully provisioned client account ${newUsername}.`);
        setNewUsername('');
        setNewEmail('');
        setNewPassword('');
      } else {
        const res = await apiClient.post('/auth/admin/create', {
          username: newUsername.trim(),
          email: newEmail.trim(),
          role: newRole.toUpperCase()
        });
        const resData = typeof res.data === 'string' ? JSON.parse(res.data) : res.data;
        addToast('success', `Successfully provisioned ${newUsername} as ${newRole}.`);
        setGeneratedKey(resData.admin_access_key);
        setGeneratedUser(newUsername.trim());
        setNewUsername('');
        setNewEmail('');
        setNewPassword('');
      }
      fetchUsers();
    } catch (err: any) {
      let errMsg = 'Provisioning failed';
      if (err.response && err.response.data) {
        const errorData = typeof err.response.data === 'string' ? JSON.parse(err.response.data) : err.response.data;
        errMsg = errorData.detail || errorData.message || errMsg;
      }
      addToast('error', `Provisioning failed: ${errMsg}`);
    } finally {
      setCreating(false);
    }
  };

  const handleToggleActive = async (username: string) => {
    try {
      await apiClient.post(`/auth/users/${username}/toggle-active`);
      addToast('success', `Toggled activation status for user ${username}.`);
      fetchUsers();
    } catch (err: any) {
      addToast('error', `Failed to toggle status: ${err.message}`);
    }
  };

  const handleRoleChange = async (username: string, updatedRole: string) => {
    try {
      await apiClient.post(`/auth/users/${username}/role`, { role: updatedRole });
      addToast('success', `Updated ${username}'s role to ${updatedRole}.`);
      fetchUsers();
    } catch (err: any) {
      addToast('error', `Role update failed: ${err.message}`);
    }
  };

  const handleResetPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!resetTargetUser || !resetPasswordVal) return;

    setResetting(true);
    try {
      await apiClient.post(`/auth/users/${resetTargetUser}/reset-password`, {
        new_password: resetPasswordVal
      });
      addToast('success', `Successfully reset password for user ${resetTargetUser}.`);
      setResetTargetUser(null);
      setResetPasswordVal('');
    } catch (err: any) {
      addToast('error', `Password reset failed: ${err.message}`);
    } finally {
      setResetting(false);
    }
  };

  // Whitelist Actions
  const handleAddIpWhitelist = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newIpAddress.trim()) return;

    setAddingIp(true);
    try {
      await apiClient.post('/security/ip-whitelist', {
        ip_address: newIpAddress.trim(),
        description: newIpDesc.trim() || 'Manual entry'
      });
      addToast('success', `Successfully whitelisted IP: ${newIpAddress}`);
      setNewIpAddress('');
      setNewIpDesc('');
      fetchWhitelist();
    } catch (err: any) {
      let errMsg = 'Failed to whitelist IP';
      if (err.response && err.response.data) {
        const errorData = typeof err.response.data === 'string' ? JSON.parse(err.response.data) : err.response.data;
        errMsg = errorData.detail || errorData.message || errMsg;
      }
      addToast('error', errMsg);
    } finally {
      setAddingIp(false);
    }
  };

  const handleDeleteIpWhitelist = async (ip: string) => {
    try {
      await apiClient.delete(`/security/ip-whitelist/${ip}`);
      addToast('success', `Successfully removed IP from whitelist: ${ip}`);
      fetchWhitelist();
    } catch (err: any) {
      addToast('error', `Failed to delete whitelisted IP: ${err.message}`);
    }
  };

  return (
    <div className="space-y-6">
      {/* HEADER */}
      <div className="flex flex-col md:flex-row md:justify-between md:items-center border-b border-zinc-900/60 pb-4 gap-4">
        <div>
          <h1 className="text-2xl font-extrabold font-display text-zinc-100 tracking-tight flex items-center gap-2">
            <Sliders className="text-cyan-400 w-6 h-6 stroke-[2]" />
            Enterprise Security Operations Center
          </h1>
          <p className="text-xs text-zinc-550 mt-1">
            GATEWAY ADMINISTRATIVE TERMINAL: PROVISION STAFF, CONFIGURE DB IP WHITELISTS, AUDIT REAL-TIME ROUTING TRAFFIC, AND MONITOR SOC METRICS.
          </p>
        </div>
        
        {/* TAB NAVIGATION SELECTOR */}
        <div className="flex items-center gap-2 font-mono text-[10px] bg-[#07070a] p-1 border border-zinc-900 rounded-xl">
          <button
            onClick={() => setActiveTab('users')}
            className={`px-3 py-1.5 rounded-lg font-bold cursor-pointer transition-all ${
              activeTab === 'users' ? 'bg-cyan-950/40 text-cyan-400 border border-cyan-800/30' : 'text-zinc-500 hover:text-zinc-350'
            }`}
          >
            Staff Registry
          </button>
          <button
            onClick={() => setActiveTab('whitelist')}
            className={`px-3 py-1.5 rounded-lg font-bold cursor-pointer transition-all ${
              activeTab === 'whitelist' ? 'bg-cyan-950/40 text-cyan-400 border border-cyan-800/30' : 'text-zinc-500 hover:text-zinc-350'
            }`}
          >
            IP Whitelist
          </button>
          <button
            onClick={() => setActiveTab('requests')}
            className={`px-3 py-1.5 rounded-lg font-bold cursor-pointer transition-all ${
              activeTab === 'requests' ? 'bg-cyan-950/40 text-cyan-400 border border-cyan-800/30' : 'text-zinc-500 hover:text-zinc-350'
            }`}
          >
            Request Monitor
          </button>
          <button
            onClick={() => setActiveTab('security')}
            className={`px-3 py-1.5 rounded-lg font-bold cursor-pointer transition-all ${
              activeTab === 'security' ? 'bg-cyan-950/40 text-cyan-400 border border-cyan-800/30' : 'text-zinc-500 hover:text-zinc-350'
            }`}
          >
            Security Console
          </button>
        </div>
      </div>

      {/* ==================== TAB 1: STAFF PROVISIONING ==================== */}
      {activeTab === 'users' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 animate-fade-in">
          {/* PROVISION USER PANEL */}
          <div className="glass-card rounded-xl p-6 lg:col-span-4 space-y-4 border-zinc-800/80 bg-zinc-950/40">
            <div className="border-b border-zinc-900 pb-2 flex items-center gap-1.5">
              <UserPlus size={16} className="text-cyan-400" />
              <h2 className="text-xs font-bold font-mono uppercase tracking-wider text-zinc-200">Provision Client/User</h2>
            </div>

            <form onSubmit={handleCreateUser} className="space-y-4 text-xs font-mono">
              {/* Username */}
              <div className="space-y-1.5">
                <label className="block text-[10px] text-zinc-500 uppercase font-bold tracking-wider">Username</label>
                <div className="relative">
                  <span className="absolute inset-y-0 left-0 pl-3 flex items-center text-zinc-650">
                    <User size={12} />
                  </span>
                  <input
                    type="text"
                    value={newUsername}
                    onChange={(e) => setNewUsername(e.target.value)}
                    placeholder="e.g. mbanking_client"
                    className="input-premium pl-9"
                    required
                  />
                </div>
              </div>

              {/* Email */}
              <div className="space-y-1.5">
                <label className="block text-[10px] text-zinc-500 uppercase font-bold tracking-wider">Email Address</label>
                <div className="relative">
                  <span className="absolute inset-y-0 left-0 pl-3 flex items-center text-zinc-650">
                    <Mail size={12} />
                  </span>
                  <input
                    type="email"
                    value={newEmail}
                    onChange={(e) => setNewEmail(e.target.value)}
                    placeholder="e.g. client@bank.com"
                    className="input-premium pl-9"
                    required
                  />
                </div>
              </div>

              {/* Password */}
              {newRole === 'CLIENT' ? (
                <div className="space-y-1.5">
                  <label className="block text-[10px] text-zinc-500 uppercase font-bold tracking-wider">Initial Password</label>
                  <div className="relative">
                    <span className="absolute inset-y-0 left-0 pl-3 flex items-center text-zinc-650">
                      <KeyRound size={12} />
                    </span>
                    <input
                      type={showPassword ? 'text' : 'password'}
                      value={newPassword}
                      onChange={(e) => setNewPassword(e.target.value)}
                      placeholder="Enter password..."
                      className="input-premium pl-9 pr-9"
                      required
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute inset-y-0 right-0 pr-3 flex items-center text-zinc-500 hover:text-zinc-350 cursor-pointer"
                    >
                      {showPassword ? <EyeOff size={12} /> : <Eye size={12} />}
                    </button>
                  </div>
                </div>
              ) : (
                <div className="p-3.5 bg-rose-950/10 border border-rose-900/20 rounded-xl text-[10.5px] text-zinc-400 leading-normal font-sans">
                  <span className="font-bold text-rose-400">Staff Account Notice:</span> Administrative accounts are provisioned as inactive. A temporary key will be generated for the user to activate their account and set their password.
                </div>
              )}

              {/* Role Selection */}
              <div className="space-y-1.5">
                <label className="block text-[10px] text-zinc-500 uppercase font-bold tracking-wider">Assigned Role</label>
                <select
                  value={newRole}
                  onChange={(e) => setNewRole(e.target.value)}
                  className="input-premium bg-zinc-950 pr-8"
                >
                  <option value="CLIENT">CLIENT — Limited Transactional API</option>
                  <option value="OPERATIONS">OPERATIONS — Manual Reconciliation & Workflow Control</option>
                  <option value="AUDITOR">AUDITOR — Read-Only Logs & Compliance Reports</option>
                  <option value="ADMIN">ADMIN — Full Gateway Control & User Provisioning</option>
                </select>
              </div>

              <button
                type="submit"
                disabled={creating}
                className="w-full mt-2 bg-gradient-to-r from-cyan-600 to-cyan-500 hover:from-cyan-500 hover:to-cyan-400 text-black font-extrabold py-2.5 px-4 rounded-xl transition-all cursor-pointer shadow-md shadow-cyan-950/20 text-center block"
              >
                {creating ? 'PROVISIONING...' : 'PROVISION USER'}
              </button>
            </form>
          </div>

          {/* USERS REGISTRY TABLE */}
          <div className="glass-card rounded-xl p-6 lg:col-span-8 space-y-4 border-zinc-800/80 bg-zinc-950/40">
            <div className="border-b border-zinc-900 pb-2 flex items-center justify-between">
              <div className="flex items-center gap-1.5">
                <UserCheck size={16} className="text-cyan-400" />
                <h2 className="text-xs font-bold font-mono uppercase tracking-wider text-zinc-200">Active User Registry</h2>
              </div>
              <span className="text-[9px] text-zinc-500 font-mono">{users.length} Users Registered</span>
            </div>

            {loadingUsers ? (
              <div className="text-zinc-650 text-xs font-mono py-16 text-center flex items-center justify-center gap-2">
                <RotateCw className="animate-spin text-zinc-650" size={14} />
                Scanning enterprise user base...
              </div>
            ) : (
              <div className="overflow-x-auto border border-zinc-900 rounded-xl bg-zinc-900/10">
                <table className="w-full text-left border-collapse font-mono text-[11px]">
                  <thead>
                    <tr className="bg-zinc-900/30 border-b border-zinc-900 text-zinc-550 uppercase tracking-wider text-[8px]">
                      <th className="px-4.5 py-2.5">User</th>
                      <th className="px-4.5 py-2.5">Role Mapping</th>
                      <th className="px-4.5 py-2.5 text-center">Status</th>
                      <th className="px-4.5 py-2.5 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-zinc-900/50">
                    {users.map((u) => {
                      const isSelf = u.username === 'admin';
                      return (
                        <tr key={u.id} className="hover:bg-zinc-900/20">
                          <td className="px-4.5 py-3">
                            <div className="font-bold text-zinc-250">{u.username}</div>
                            <div className="text-[9px] text-zinc-555 mt-0.5">{u.email}</div>
                          </td>
                          <td className="px-4.5 py-3 whitespace-nowrap">
                            <select
                              value={u.role}
                              onChange={(e) => handleRoleChange(u.username, e.target.value)}
                              disabled={isSelf}
                              className="bg-[#050507] border border-zinc-800 text-[10px] text-zinc-400 rounded px-1.5 py-0.5 font-bold font-mono focus:outline-none focus:border-cyan-500 cursor-pointer disabled:cursor-not-allowed disabled:opacity-50"
                            >
                              <option value="CLIENT">CLIENT</option>
                              <option value="OPERATIONS">OPERATIONS</option>
                              <option value="AUDITOR">AUDITOR</option>
                              <option value="ADMIN">ADMIN</option>
                            </select>
                          </td>
                          <td className="px-4.5 py-3 text-center">
                            <span className={`px-2 py-0.5 rounded text-[8px] font-bold ${
                              u.is_active 
                                ? 'bg-emerald-950/20 text-emerald-400 border border-emerald-900/30' 
                                : 'bg-rose-950/20 text-rose-400 border border-rose-900/30 animate-pulse'
                            }`}>
                              {u.is_active ? 'ACTIVE' : 'DEACTIVATED'}
                            </span>
                          </td>
                          <td className="px-4.5 py-3 text-right whitespace-nowrap space-x-1.5">
                            <button
                              onClick={() => handleToggleActive(u.username)}
                              disabled={isSelf}
                              className={`p-1 rounded cursor-pointer transition-colors disabled:opacity-40 disabled:cursor-not-allowed ${
                                u.is_active 
                                  ? 'bg-rose-950/40 text-rose-500 border border-rose-900/30 hover:bg-rose-900/20' 
                                  : 'bg-emerald-950/40 text-emerald-500 border border-emerald-900/30 hover:bg-emerald-900/20'
                              }`}
                              title={u.is_active ? 'Deactivate User' : 'Activate User'}
                            >
                              {u.is_active ? <UserX size={12} /> : <UserCheck size={12} />}
                            </button>
                            <button
                              onClick={() => {
                                setResetTargetUser(u.username);
                                setResetPasswordVal('');
                              }}
                              className="p-1 rounded bg-zinc-900 text-zinc-450 border border-zinc-800 hover:text-zinc-200 hover:bg-zinc-850 cursor-pointer"
                              title="Reset Password"
                            >
                              <KeyRound size={12} />
                            </button>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ==================== TAB 2: IP WHITELIST MANAGEMENT ==================== */}
      {activeTab === 'whitelist' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 animate-fade-in">
          {/* ADD IP CARD */}
          <div className="glass-card rounded-xl p-6 lg:col-span-4 space-y-4 border-zinc-800/80 bg-zinc-950/40">
            <div className="border-b border-zinc-900 pb-2 flex items-center gap-1.5">
              <Globe size={16} className="text-cyan-400" />
              <h2 className="text-xs font-bold font-mono uppercase tracking-wider text-zinc-200">Whitelist Client IP</h2>
            </div>

            <form onSubmit={handleAddIpWhitelist} className="space-y-4 text-xs font-mono">
              <div className="space-y-1.5">
                <label className="block text-[10px] text-zinc-500 uppercase font-bold tracking-wider">IPv4 Address</label>
                <div className="relative">
                  <span className="absolute inset-y-0 left-0 pl-3 flex items-center text-zinc-650">
                    <Globe size={12} />
                  </span>
                  <input
                    type="text"
                    value={newIpAddress}
                    onChange={(e) => setNewIpAddress(e.target.value)}
                    placeholder="e.g. 206.1.1.4"
                    className="input-premium pl-9"
                    required
                  />
                </div>
              </div>

              <div className="space-y-1.5">
                <label className="block text-[10px] text-zinc-500 uppercase font-bold tracking-wider">Description / Tag</label>
                <input
                  type="text"
                  value={newIpDesc}
                  onChange={(e) => setNewIpDesc(e.target.value)}
                  placeholder="e.g. Production Mobile Channel"
                  className="input-premium"
                />
              </div>

              <button
                type="submit"
                disabled={addingIp}
                className="w-full mt-2 bg-gradient-to-r from-cyan-600 to-cyan-500 hover:from-cyan-500 hover:to-cyan-400 text-black font-extrabold py-2.5 px-4 rounded-xl transition-all cursor-pointer shadow-md shadow-cyan-950/20 flex items-center justify-center gap-1.5"
              >
                {addingIp ? <RotateCw className="animate-spin" size={12} /> : <Plus size={12} />}
                <span>WHITELIST IP ADDRESS</span>
              </button>
            </form>

            <div className="p-3.5 bg-cyan-950/10 border border-cyan-900/20 rounded-xl text-[10px] text-zinc-500 leading-normal font-sans space-y-1">
              <span className="font-bold text-cyan-400 flex items-center gap-1.5">
                <Info size={12} /> Security Notice
              </span>
              <p>
                Any transaction incoming from an IP not present in this whitelist (and not originating from private networks or allowed Vercel origins) will be strictly blocked with a 403 Forbidden error, and the attempt will be logged globally.
              </p>
            </div>
          </div>

          {/* WHITELIST ENTRIES TABLE */}
          <div className="glass-card rounded-xl p-6 lg:col-span-8 space-y-4 border-zinc-800/80 bg-zinc-950/40">
            <div className="border-b border-zinc-900 pb-2 flex items-center justify-between">
              <div className="flex items-center gap-1.5">
                <ShieldCheck size={16} className="text-cyan-400" />
                <h2 className="text-xs font-bold font-mono uppercase tracking-wider text-zinc-200">Whitelisted Gateway IPs</h2>
              </div>
              <span className="text-[9px] text-zinc-500 font-mono">{whitelist.length} Whitelisted IPs</span>
            </div>

            {loadingWhitelist ? (
              <div className="text-zinc-650 text-xs font-mono py-16 text-center flex items-center justify-center gap-2">
                <RotateCw className="animate-spin text-zinc-650" size={14} />
                Scanning whitelist database table...
              </div>
            ) : whitelist.length === 0 ? (
              <div className="text-zinc-550 text-xs py-16 text-center font-sans border border-dashed border-zinc-900 rounded-xl">
                No IP addresses whitelisted. Standard network connections will be blocked!
              </div>
            ) : (
              <div className="overflow-x-auto border border-zinc-900 rounded-xl bg-zinc-900/10">
                <table className="w-full text-left border-collapse font-mono text-[11px]">
                  <thead>
                    <tr className="bg-zinc-900/30 border-b border-zinc-900 text-zinc-550 uppercase tracking-wider text-[8px]">
                      <th className="px-4.5 py-2.5">IP Address</th>
                      <th className="px-4.5 py-2.5">Description</th>
                      <th className="px-4.5 py-2.5">Added By</th>
                      <th className="px-4.5 py-2.5">Created At</th>
                      <th className="px-4.5 py-2.5 text-right">Delete</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-zinc-900/50">
                    {whitelist.map((item) => {
                      const isLocal = ['127.0.0.1', 'localhost', '::1', 'testclient'].includes(item.ip_address);
                      return (
                        <tr key={item.id} className="hover:bg-zinc-900/20">
                          <td className="px-4.5 py-3 font-bold text-zinc-200">{item.ip_address}</td>
                          <td className="px-4.5 py-3 text-zinc-450">{item.description}</td>
                          <td className="px-4.5 py-3 text-zinc-450">{item.added_by}</td>
                          <td className="px-4.5 py-3 text-zinc-550">{new Date(item.created_at).toLocaleString()}</td>
                          <td className="px-4.5 py-3 text-right">
                            <button
                              onClick={() => handleDeleteIpWhitelist(item.ip_address)}
                              disabled={isLocal}
                              className="text-rose-500 hover:text-rose-400 p-1 cursor-pointer disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                              title={isLocal ? "System loopback IPs cannot be removed" : "Remove IP from whitelist"}
                            >
                              <Trash2 size={12} />
                            </button>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ==================== TAB 3: REQUEST MONITORING ==================== */}
      {activeTab === 'requests' && (
        <div className="glass-card rounded-xl p-6 border-zinc-800/80 bg-zinc-950/40 space-y-4 animate-fade-in">
          <div className="border-b border-zinc-900 pb-2 flex items-center justify-between">
            <div className="flex items-center gap-1.5">
              <Activity size={16} className="text-cyan-400" />
              <h2 className="text-xs font-bold font-mono uppercase tracking-wider text-zinc-200">Gateway Traffic Logs (Real-time Telemetry)</h2>
            </div>
            <button
              onClick={fetchRequestLogs}
              disabled={loadingRequests}
              className="border border-zinc-800 bg-zinc-900/60 hover:bg-zinc-850 text-zinc-300 rounded px-2.5 py-1 text-[9px] cursor-pointer transition-colors font-mono flex items-center gap-1"
            >
              <RotateCw size={10} className={loadingRequests ? 'animate-spin' : ''} />
              <span>Refresh Logs</span>
            </button>
          </div>

          {loadingRequests && requestLogs.length === 0 ? (
            <div className="text-zinc-650 text-xs font-mono py-16 text-center flex items-center justify-center gap-2">
              <RotateCw className="animate-spin text-zinc-650" size={14} />
              Scanning gateway traffic logs...
            </div>
          ) : requestLogs.length === 0 ? (
            <div className="text-zinc-550 text-xs py-16 text-center font-sans border border-dashed border-zinc-900 rounded-xl">
              Gateway has not logged any routing requests yet. Send API traffic to display logs.
            </div>
          ) : (
            <div className="overflow-x-auto border border-zinc-900 rounded-xl bg-[#030305]">
              <table className="w-full text-left border-collapse font-mono text-[11px] text-zinc-400">
                <thead>
                  <tr className="bg-zinc-900/30 border-b border-zinc-900 text-zinc-500 uppercase tracking-wider text-[8px]">
                    <th className="px-4.5 py-2.5">Timestamp</th>
                    <th className="px-4.5 py-2.5">Request ID</th>
                    <th className="px-4.5 py-2.5">Client/User</th>
                    <th className="px-4.5 py-2.5">Source IP</th>
                    <th className="px-4.5 py-2.5">Endpoint</th>
                    <th className="px-4.5 py-2.5">Status</th>
                    <th className="px-4.5 py-2.5 text-center">Code</th>
                    <th className="px-4.5 py-2.5 text-right">Latency</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-zinc-900/60">
                  {requestLogs.map((log) => {
                    const isSuccess = log.request_status === 'SUCCESS';
                    const isBlocked = log.request_status === 'BLOCKED';
                    const isUnauth = log.request_status === 'UNAUTHORIZED';
                    const isFailed = log.request_status === 'FAILED' || log.request_status === 'ERROR';
                    
                    let statusBadgeClass = 'badge-premium-zinc';
                    if (isSuccess) statusBadgeClass = 'badge-premium-emerald';
                    else if (isBlocked) statusBadgeClass = 'badge-premium-amber animate-pulse';
                    else if (isUnauth) statusBadgeClass = 'badge-premium-purple';
                    else if (isFailed) statusBadgeClass = 'badge-premium-rose';

                    return (
                      <tr key={log.id} className="hover:bg-zinc-900/10">
                        <td className="px-4.5 py-2.5 text-zinc-550 whitespace-nowrap">
                          {new Date(log.timestamp).toLocaleTimeString()}
                        </td>
                        <td className="px-4.5 py-2.5 text-zinc-300 font-bold select-all" title={log.request_id}>
                          {log.request_id.slice(0, 15)}...
                        </td>
                        <td className="px-4.5 py-2.5 text-zinc-350">{log.client_user}</td>
                        <td className="px-4.5 py-2.5 text-zinc-450 font-sans">{log.source_ip}</td>
                        <td className="px-4.5 py-2.5 text-cyan-400 font-bold max-w-xs truncate" title={log.endpoint}>
                          {log.endpoint}
                        </td>
                        <td className="px-4.5 py-2.5 whitespace-nowrap">
                          <span className={`badge-premium ${statusBadgeClass}`}>
                            {log.request_status}
                          </span>
                        </td>
                        <td className="px-4.5 py-2.5 text-center text-zinc-300 font-bold">{log.response_code || '-'}</td>
                        <td className="px-4.5 py-2.5 text-right text-zinc-400 font-sans">
                          {log.processing_time_ms ? `${log.processing_time_ms.toFixed(1)} ms` : '-'}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}

          {/* Pagination Controls */}
          <div className="flex justify-between items-center text-[10px] font-mono text-zinc-500 pt-2 border-t border-zinc-900">
            <span>Showing Page {logPage + 1}</span>
            <div className="flex gap-2">
              <button 
                onClick={() => setLogPage(p => Math.max(0, p - 1))}
                disabled={logPage === 0}
                className="px-3 py-1 bg-zinc-900/40 border border-zinc-800 rounded hover:bg-zinc-800 disabled:opacity-30 disabled:cursor-not-allowed cursor-pointer"
              >
                PREVIOUS
              </button>
              <button 
                onClick={() => setLogPage(p => p + 1)}
                disabled={requestLogs.length < logLimit}
                className="px-3 py-1 bg-zinc-900/40 border border-zinc-800 rounded hover:bg-zinc-800 disabled:opacity-30 disabled:cursor-not-allowed cursor-pointer"
              >
                NEXT
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ==================== TAB 4: SECURITY OPERATIONS DASHBOARD ==================== */}
      {activeTab === 'security' && (
        <div className="space-y-6 animate-fade-in font-mono text-xs">
          {/* Stats Metrics Cards */}
          <div className="grid grid-cols-2 md:grid-cols-5 gap-5">
            <div className="glass-card rounded-xl p-5 flex flex-col justify-between h-28 border-zinc-800 bg-zinc-950/40 shadow-sm">
              <span className="text-zinc-550 text-[9px] uppercase tracking-wider block">Active Users</span>
              <div>
                <h3 className="text-2xl font-black text-cyan-400">{securityStats?.active_users ?? 0}</h3>
                <span className="text-[8px] text-zinc-600 block mt-1 font-sans">Enabled in DB user registry</span>
              </div>
            </div>
            
            <div className="glass-card rounded-xl p-5 flex flex-col justify-between h-28 border-zinc-800 bg-zinc-950/40 shadow-sm">
              <span className="text-zinc-550 text-[9px] uppercase tracking-wider block">Active Sessions</span>
              <div>
                <h3 className="text-2xl font-black text-blue-400">{securityStats?.active_sessions ?? 0}</h3>
                <span className="text-[8px] text-zinc-600 block mt-1 font-sans">Concurrent user logins</span>
              </div>
            </div>

            <div className="glass-card rounded-xl p-5 flex flex-col justify-between h-28 border-zinc-800 bg-zinc-950/40 shadow-sm">
              <span className="text-zinc-550 text-[9px] uppercase tracking-wider block">Whitelisted IPs</span>
              <div>
                <h3 className="text-2xl font-black text-emerald-400">{securityStats?.active_ips ?? 0}</h3>
                <span className="text-[8px] text-zinc-600 block mt-1 font-sans">Authoritative firewalled nodes</span>
              </div>
            </div>

            <div className="glass-card rounded-xl p-5 flex flex-col justify-between h-28 border-zinc-800 bg-zinc-950/40 shadow-sm">
              <span className="text-zinc-550 text-[9px] uppercase tracking-wider block">Failed Logins</span>
              <div>
                <h3 className="text-2xl font-black text-rose-500">{securityStats?.failed_login_count ?? 0}</h3>
                <span className="text-[8px] text-zinc-600 block mt-1 font-sans">Bad password/credential attempts</span>
              </div>
            </div>

            <div className="glass-card rounded-xl p-5 flex flex-col justify-between h-28 border-zinc-800 bg-zinc-950/40 shadow-sm">
              <span className="text-zinc-550 text-[9px] uppercase tracking-wider block">Blocked IP Attacks</span>
              <div>
                <h3 className="text-2xl font-black text-rose-550 animate-pulse">{securityStats?.blocked_ip_count ?? 0}</h3>
                <span className="text-[8px] text-zinc-600 block mt-1 font-sans">Blocked access requests</span>
              </div>
            </div>
          </div>
          
          {/* API Usage Metrics */}
          {securityStats && securityStats.api_usage_statistics && (
            <div className="glass-card rounded-xl p-6 border-zinc-800/80 bg-zinc-950/40 space-y-4">
              <div className="border-b border-zinc-900 pb-2 flex items-center justify-between">
                <div className="flex items-center gap-1.5 text-cyan-400">
                  <Activity size={16} />
                  <h2 className="text-xs font-bold uppercase tracking-wider text-zinc-200">API Gateway Volume (All Time)</h2>
                </div>
              </div>
              <div className="flex gap-4 overflow-x-auto pb-2">
                {Object.entries(securityStats.api_usage_statistics).map(([status, count]) => {
                  let color = "text-zinc-400";
                  if (status === "SUCCESS") color = "text-emerald-400";
                  if (status === "BLOCKED" || status === "UNAUTHORIZED") color = "text-amber-400";
                  if (status === "FAILED" || status === "ERROR") color = "text-rose-400";
                  return (
                    <div key={status} className="bg-[#050507] border border-zinc-900 rounded-lg p-3 min-w-[120px] flex-shrink-0">
                      <span className="text-[9px] uppercase text-zinc-500 font-bold block mb-1">{status}</span>
                      <span className={`text-lg font-black ${color}`}>{count}</span>
                    </div>
                  );
                })}
                {Object.keys(securityStats.api_usage_statistics).length === 0 && (
                  <div className="text-zinc-600 text-xs italic">No API usage data available.</div>
                )}
              </div>
            </div>
          )}

          {/* Audited Security events feed */}
          <div className="glass-card rounded-xl p-6 border-zinc-800/80 bg-zinc-950/40 space-y-4">
            <div className="border-b border-zinc-900 pb-2 flex items-center justify-between">
              <div className="flex items-center gap-1.5 text-rose-400">
                <ShieldAlert size={16} />
                <h2 className="text-xs font-bold uppercase tracking-wider text-zinc-200">Security Events Ledger (SOC Audit)</h2>
              </div>
              <button
                onClick={fetchSecurityStats}
                disabled={loadingStats}
                className="border border-zinc-800 bg-zinc-900/60 hover:bg-zinc-850 text-zinc-300 rounded px-2.5 py-1 text-[9px] cursor-pointer transition-colors font-mono flex items-center gap-1"
              >
                <RotateCw size={10} className={loadingStats ? 'animate-spin' : ''} />
                <span>Reload SOC Feed</span>
              </button>
            </div>

            {loadingStats && !securityStats ? (
              <div className="text-zinc-650 text-xs font-mono py-16 text-center flex items-center justify-center gap-2">
                <RotateCw className="animate-spin text-zinc-650" size={14} />
                Scanning audit ledger tables...
              </div>
            ) : !securityStats || securityStats.recent_events.length === 0 ? (
              <div className="text-zinc-550 text-xs py-16 text-center font-sans border border-dashed border-zinc-900 rounded-xl">
                Security event ledger is clear. No alerts recorded yet.
              </div>
            ) : (
              <div className="overflow-x-auto border border-zinc-900 rounded-xl bg-[#030305]">
                <table className="w-full text-left border-collapse font-mono text-[11px] text-zinc-400">
                  <thead>
                    <tr className="bg-zinc-900/30 border-b border-zinc-900 text-zinc-550 uppercase tracking-wider text-[8px]">
                      <th className="px-4.5 py-2.5">Event Timestamp</th>
                      <th className="px-4.5 py-2.5">User</th>
                      <th className="px-4.5 py-2.5">Access Role</th>
                      <th className="px-4.5 py-2.5">Action Event</th>
                      <th className="px-4.5 py-2.5">Client IP</th>
                      <th className="px-4.5 py-2.5">Compliance Logs / Details</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-zinc-900/50">
                    {securityStats.recent_events.map((evt) => {
                      const isAlert = ['IP_BLOCKED', 'CLIENT_LOGIN_FAILED', 'ADMIN_LOGIN_FAILED', 'REPORT_DECRYPTION_FAILED'].includes(evt.action);
                      return (
                        <tr key={evt.id} className="hover:bg-zinc-900/10">
                          <td className="px-4.5 py-2.5 text-zinc-550 whitespace-nowrap">
                            {new Date(evt.timestamp).toLocaleString()}
                          </td>
                          <td className="px-4.5 py-2.5 font-bold text-zinc-350">{evt.username}</td>
                          <td className="px-4.5 py-2.5 text-zinc-450">{evt.role}</td>
                          <td className="px-4.5 py-2.5 whitespace-nowrap">
                            <span className={`px-2 py-0.5 rounded text-[8px] font-bold ${
                              isAlert 
                                ? 'bg-rose-950/20 text-rose-400 border border-rose-900/30 animate-pulse' 
                                : 'bg-emerald-950/20 text-emerald-400 border border-emerald-900/30'
                            }`}>
                              {evt.action}
                            </span>
                          </td>
                          <td className="px-4.5 py-2.5 text-zinc-450 font-sans">{evt.ip_address || '-'}</td>
                          <td className="px-4.5 py-2.5 text-zinc-300 font-sans truncate max-w-xs" title={evt.details}>
                            {evt.details}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {/* RESET PASSWORD MODAL DIALOG */}
      {resetTargetUser && (
        <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4 font-mono text-xs">
          <div className="glass-card rounded-xl p-6 border-zinc-800 bg-[#09090b] max-w-sm w-full space-y-4 shadow-xl">
            <div className="flex items-center gap-1.5 border-b border-zinc-900 pb-2">
              <KeyRound size={16} className="text-cyan-400" />
              <h3 className="text-xs font-bold text-zinc-100 uppercase tracking-wider">Reset Credentials</h3>
            </div>
            
            <p className="text-[11px] text-zinc-400 font-sans leading-relaxed">
              Define a new access password for user: <strong className="text-cyan-400 font-mono">{resetTargetUser}</strong>.
            </p>

            <form onSubmit={handleResetPassword} className="space-y-4">
              <div className="space-y-1.5">
                <label className="block text-[10px] text-zinc-550 uppercase font-bold tracking-wider">New Password</label>
                <input
                  type="text"
                  value={resetPasswordVal}
                  onChange={(e) => setResetPasswordVal(e.target.value)}
                  placeholder="Min 6 characters..."
                  className="input-premium font-mono"
                  required
                />
              </div>

              <div className="flex justify-end gap-2 text-[10px] font-bold">
                <button
                  type="button"
                  onClick={() => setResetTargetUser(null)}
                  className="border border-zinc-800 text-zinc-400 hover:text-zinc-200 py-2 px-4 rounded-lg cursor-pointer"
                >
                  CANCEL
                </button>
                <button
                  type="submit"
                  disabled={resetting}
                  className="bg-cyan-600 hover:bg-cyan-500 text-black py-2 px-4 rounded-lg cursor-pointer flex items-center gap-1"
                >
                  {resetting ? <RotateCw className="animate-spin" size={10} /> : null}
                  <span>CONFIRM RESET</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ACCESS KEY COPY MODAL */}
      {generatedKey && (
        <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4 font-mono text-xs">
          <div className="glass-card rounded-xl p-6 border-rose-800 bg-[#09090b] max-w-md w-full space-y-4 shadow-xl">
            <div className="flex items-center gap-1.5 border-b border-zinc-900 pb-2 text-rose-400">
              <ShieldAlert size={16} />
              <h3 className="text-xs font-bold uppercase tracking-wider">Secret Provisioning Key Generated</h3>
            </div>
            
            <div className="bg-rose-950/10 border border-rose-900/20 p-4 rounded-xl space-y-2 leading-relaxed text-zinc-400 font-sans text-xs">
              <p>A new secure access key has been generated for: <strong className="text-rose-400 font-mono">{generatedUser}</strong>.</p>
              <p className="text-rose-350 font-bold flex items-center gap-1.5 mt-2">
                <ShieldAlert size={14} />
                <span>CRITICAL: Copy this key now! It will NOT be shown again.</span>
              </p>
            </div>

            <div className="space-y-1.5">
              <label className="block text-[10px] text-zinc-555 uppercase font-bold tracking-wider">ADMIN_ACCESS_KEY</label>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={generatedKey}
                  readOnly
                  className="input-premium font-mono bg-zinc-950 text-rose-300 font-bold border-rose-900/40 select-all"
                />
              </div>
            </div>

            <div className="flex justify-end pt-2">
              <button
                type="button"
                onClick={() => { setGeneratedKey(null); setGeneratedUser(null); }}
                className="bg-rose-600 hover:bg-rose-500 text-black py-2 px-6 rounded-lg cursor-pointer text-[10px] font-bold font-mono"
              >
                DISMISS KEY
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default AdminProvisioning;
