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
  EyeOff
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

export const AdminProvisioning: React.FC = () => {
  const [users, setUsers] = useState<UserItem[]>([]);
  const [loading, setLoading] = useState(false);

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

  const { addToast } = useToastStore();

  const fetchUsers = async () => {
    setLoading(true);
    try {
      const response = await apiClient.get('/auth/users');
      setUsers(response.data);
    } catch (err: any) {
      addToast('error', `Failed to load users: ${err.response?.data?.detail || err.message}`);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
  }, []);

  const handleCreateUser = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newUsername || !newEmail || !newPassword) {
      addToast('error', 'Please fill in all provisioning fields.');
      return;
    }

    setCreating(true);
    try {
      await apiClient.post('/auth/signup', {
        username: newUsername,
        email: newEmail,
        password: newPassword,
        role: newRole
      });
      addToast('success', `Successfully provisioned ${newUsername} as ${newRole}.`);
      setNewUsername('');
      setNewEmail('');
      setNewPassword('');
      fetchUsers();
    } catch (err: any) {
      addToast('error', `Provisioning failed: ${err.response?.data?.detail || err.message}`);
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
      addToast('error', `Failed to toggle status: ${err.response?.data?.detail || err.message}`);
    }
  };

  const handleRoleChange = async (username: string, updatedRole: string) => {
    try {
      await apiClient.post(`/auth/users/${username}/role`, { role: updatedRole });
      addToast('success', `Updated ${username}'s role to ${updatedRole}.`);
      fetchUsers();
    } catch (err: any) {
      addToast('error', `Role update failed: ${err.response?.data?.detail || err.message}`);
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
      addToast('error', `Password reset failed: ${err.response?.data?.detail || err.message}`);
    } finally {
      setResetting(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* HEADER */}
      <div className="flex flex-col md:flex-row md:justify-between md:items-center border-b border-zinc-900/60 pb-4 gap-4">
        <div>
          <h1 className="text-2xl font-extrabold font-display text-zinc-100 tracking-tight flex items-center gap-2">
            <Sliders className="text-cyan-400 w-6 h-6 stroke-[2]" />
            Enterprise Provisioning Portal
          </h1>
          <p className="text-xs text-zinc-550 mt-1">
            ADMIN CENTRAL SECURITY OPERATIONS: REGISTER CLIENTS, ASSIGN ROLES, TOGGLE LIFECYCLES, AND RESET CREDENTIALS.
          </p>
        </div>
        <button
          onClick={fetchUsers}
          disabled={loading}
          className="border border-zinc-800 bg-zinc-900/60 hover:bg-zinc-800 text-zinc-300 rounded-lg px-3.5 py-1.5 text-[11px] cursor-pointer transition-colors font-mono flex items-center gap-1.5"
        >
          <RotateCw size={12} className={loading ? 'animate-spin' : ''} />
          <span>Reload Registry</span>
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* PROVISION USER PANEL */}
        <div className="glass-card rounded-xl p-6 lg:col-span-4 space-y-4">
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
                  placeholder="Secret access key..."
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
        <div className="glass-card rounded-xl p-6 lg:col-span-8 space-y-4 flex flex-col justify-between">
          <div className="space-y-4">
            <div className="border-b border-zinc-900 pb-2 flex items-center justify-between">
              <div className="flex items-center gap-1.5">
                <UserCheck size={16} className="text-cyan-400" />
                <h2 className="text-xs font-bold font-mono uppercase tracking-wider text-zinc-200">Active User Registry</h2>
              </div>
              <span className="text-[9px] text-zinc-500 font-mono">{users.length} Users Seeded</span>
            </div>

            {loading ? (
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
                      const isSelf = u.username === 'admin'; // protect default admin
                      return (
                        <tr key={u.id} className="hover:bg-zinc-900/20">
                          <td className="px-4.5 py-3">
                            <div className="font-bold text-zinc-250">{u.username}</div>
                            <div className="text-[9px] text-zinc-550 mt-0.5">{u.email}</div>
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
      </div>

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

      {/* PERMISSIONS MATRIX OVERVIEW */}
      <div className="glass-card rounded-xl p-6 space-y-4 border-zinc-800 bg-zinc-950/20">
        <div className="border-b border-zinc-900 pb-2.5 flex items-center gap-1.5">
          <Info size={16} className="text-cyan-400" strokeWidth={2.5} />
          <h2 className="text-xs font-bold font-mono uppercase tracking-wider text-zinc-200">Role-Based Access Matrix (Zero-Trust Overview)</h2>
        </div>

        <div className="overflow-x-auto text-[10.5px] font-mono">
          <table className="w-full text-left border border-zinc-900 rounded-lg">
            <thead>
              <tr className="bg-zinc-900/30 border-b border-zinc-900 text-zinc-550 select-none uppercase tracking-wider text-[8px]">
                <th className="px-4 py-2">Role Clearance</th>
                <th className="px-4 py-2">Core API Paths Permitted</th>
                <th className="px-4 py-2">System Operations Controls</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-900/60">
              <tr>
                <td className="px-4 py-3 font-bold text-emerald-400 whitespace-nowrap">CLIENT</td>
                <td className="px-4 py-3 text-zinc-400">`/fetch`, `/pay`, `/favorite-billers`, `/prepaid-plans`, `/oneview`</td>
                <td className="px-4 py-3 text-zinc-550 leading-relaxed font-sans">Consumer transaction entries. Cannot access backend administrative, security testing, or data seeding channels.</td>
              </tr>
              <tr>
                <td className="px-4 py-3 font-bold text-amber-500 whitespace-nowrap">OPERATIONS</td>
                <td className="px-4 py-3 text-zinc-300">All Client routes + `/reconcile`, `/billers/file/:fileid`</td>
                <td className="px-4 py-3 text-zinc-450 leading-relaxed font-sans">Read-write transaction reconciliations, retry queue checks, and download file operations status.</td>
              </tr>
              <tr>
                <td className="px-4 py-3 font-bold text-purple-400 whitespace-nowrap">AUDITOR</td>
                <td className="px-4 py-3 text-zinc-300">`/oneview`, `/transactions` (read-only audit trails)</td>
                <td className="px-4 py-3 text-zinc-450 leading-relaxed font-sans">Full compliance reads, security audit logging visibility, and cryptographic signature verification logs. Zero mutations.</td>
              </tr>
              <tr>
                <td className="px-4 py-3 font-bold text-cyan-400 whitespace-nowrap">ADMIN</td>
                <td className="px-4 py-3 text-zinc-150">All system APIs, `/auth/signup`, `/auth/users/*`</td>
                <td className="px-4 py-3 text-zinc-300 leading-relaxed font-sans font-bold">User provisioning, role adjustments, account activations/deactivations, security status overrides, cache seed commands.</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default AdminProvisioning;
