import React, { useEffect, useState } from 'react';
import { 
  ShieldAlert, 
  UserPlus, 
  KeyRound, 
  RotateCw, 
  Activity, 
  Trash2, 
  Eye, 
  CheckCircle,
  Clock,
  Terminal,
  Settings,
  ShieldCheck,
  AlertTriangle
} from 'lucide-react';
import apiClient from '../api/apiClient';
import { useToastStore } from '../state/toastStore';

interface AdminKeyItem {
  id: string;
  user_id: string;
  username: string | null;
  key_hash: string;
  is_active: boolean;
  expires_at: string | null;
  created_at: string;
}

interface AuditLogItem {
  id: string;
  username: string;
  role: string;
  action: string;
  details: string | null;
  ip_address: string | null;
  created_at: string;
}

export const SuperAdminConsole: React.FC = () => {
  const [keysList, setKeysList] = useState<AdminKeyItem[]>([]);
  const [logsList, setLogsList] = useState<AuditLogItem[]>([]);
  const [loadingKeys, setLoadingKeys] = useState(false);
  const [loadingLogs, setLoadingLogs] = useState(false);

  // Form states for provisioning administrative users
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [role, setRole] = useState('ADMIN');
  const [provisioning, setProvisioning] = useState(false);
  
  // Modal for displaying newly generated secret admin key
  const [generatedKey, setGeneratedKey] = useState<string | null>(null);
  const [generatedUser, setGeneratedUser] = useState<string | null>(null);

  // Standalone provisioning key states
  const [standaloneRole, setStandaloneRole] = useState('ADMIN');
  const [generatingKeyOnly, setGeneratingKeyOnly] = useState(false);

  const { addToast } = useToastStore();

  const fetchKeys = async () => {
    setLoadingKeys(true);
    try {
      const res = await apiClient.get('/auth/admin/keys');
      setKeysList(res.data);
    } catch (err: any) {
      addToast('error', `Failed to load admin keys: ${err.response?.data?.detail || err.message}`);
    } finally {
      setLoadingKeys(false);
    }
  };

  const fetchLogs = async () => {
    setLoadingLogs(true);
    try {
      const res = await apiClient.get('/auth/admin/logs');
      setLogsList(res.data);
    } catch (err: any) {
      addToast('error', `Failed to load audit logs: ${err.response?.data?.detail || err.message}`);
    } finally {
      setLoadingLogs(false);
    }
  };

  useEffect(() => {
    fetchKeys();
    fetchLogs();
  }, []);

  const handleCreateAdmin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username.trim() || !email.trim()) {
      addToast('error', 'Please fill in all staff provisioning fields.');
      return;
    }

    setProvisioning(true);
    try {
      const res = await apiClient.post('/auth/admin/create', {
        username: username.trim(),
        email: email.trim(),
        role: role.toUpperCase()
      });

      addToast('success', `Provisioned operational account ${username} successfully.`);
      setGeneratedKey(res.data.admin_access_key);
      setGeneratedUser(username.trim());
      
      // Reset form
      setUsername('');
      setEmail('');
      
      fetchKeys();
      fetchLogs();
    } catch (err: any) {
      addToast('error', `Provisioning failed: ${err.response?.data?.detail || err.message}`);
    } finally {
      setProvisioning(false);
    }
  };

  const handleGenerateStandaloneKey = async (e: React.FormEvent) => {
    e.preventDefault();
    setGeneratingKeyOnly(true);
    try {
      const res = await apiClient.post('/auth/admin/generate-key', {
        role: standaloneRole
      });

      addToast('success', `Generated standalone access key for role ${standaloneRole} successfully.`);
      setGeneratedKey(res.data.admin_access_key);
      setGeneratedUser(`[Unassigned key for ${standaloneRole}]`);
      
      fetchKeys();
      fetchLogs();
    } catch (err: any) {
      addToast('error', `Failed to generate standalone key: ${err.response?.data?.detail || err.message}`);
    } finally {
      setGeneratingKeyOnly(false);
    }
  };

  const handleRegenerateKey = async (targetUsername: string) => {
    if (!window.confirm(`Are you sure you want to regenerate key for user '${targetUsername}'? The old key will immediately stop working.`)) {
      return;
    }

    try {
      const res = await apiClient.post(`/auth/admin/users/${targetUsername}/regenerate-key`);
      addToast('success', `Regenerated access key for administrative user ${targetUsername}.`);
      setGeneratedKey(res.data.admin_access_key);
      setGeneratedUser(targetUsername);
      
      fetchKeys();
      fetchLogs();
    } catch (err: any) {
      addToast('error', `Key regeneration failed: ${err.response?.data?.detail || err.message}`);
    }
  };

  const handleDeleteAdmin = async (targetUsername: string) => {
    if (!window.confirm(`Are you sure you want to delete administrative user '${targetUsername}'? This action cannot be undone.`)) {
      return;
    }

    try {
      await apiClient.delete(`/auth/admin/users/${targetUsername}`);
      addToast('success', `Successfully deleted operational user account '${targetUsername}'.`);
      fetchKeys();
      fetchLogs();
    } catch (err: any) {
      addToast('error', `Deletion failed: ${err.response?.data?.detail || err.message}`);
    }
  };

  return (
    <div className="space-y-6">
      {/* HEADER */}
      <div className="flex flex-col md:flex-row md:justify-between md:items-center border-b border-zinc-900/60 pb-4 gap-4">
        <div>
          <h1 className="text-2xl font-extrabold font-display text-zinc-100 tracking-tight flex items-center gap-2">
            <Settings className="text-rose-500 w-6 h-6 stroke-[2]" />
            Super Admin Console
          </h1>
          <p className="text-xs text-zinc-550 mt-1 uppercase font-mono">
            Ecosystem Central Command: Provision admins, rotate secret clearance access keys, and review security audit logs.
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => { fetchKeys(); fetchLogs(); }}
            className="border border-zinc-800 bg-zinc-900/60 hover:bg-zinc-850 text-zinc-300 rounded-lg px-3.5 py-1.5 text-[11px] cursor-pointer transition-colors font-mono flex items-center gap-1.5"
          >
            <RotateCw size={12} />
            <span>Sync Commands</span>
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* PROVISION STAFF & KEY ONLY PANEL */}
        <div className="lg:col-span-4 space-y-6">
          <div className="glass-card rounded-xl p-6 space-y-4">
            <div className="border-b border-zinc-900 pb-2 flex items-center gap-1.5">
              <UserPlus size={16} className="text-rose-500" />
              <h2 className="text-xs font-bold font-mono uppercase tracking-wider text-zinc-200">Provision Admin/Staff</h2>
            </div>

            <form onSubmit={handleCreateAdmin} className="space-y-4 text-xs font-mono">
              {/* Username */}
              <div className="space-y-1.5">
                <label className="block text-[10px] text-zinc-500 uppercase font-bold tracking-wider">Username</label>
                <input
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="e.g. operations_lead"
                  className="input-premium"
                  required
                />
              </div>

              {/* Email */}
              <div className="space-y-1.5">
                <label className="block text-[10px] text-zinc-500 uppercase font-bold tracking-wider">Email</label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="e.g. lead@bbps-gateway.in"
                  className="input-premium"
                  required
                />
              </div>

              {/* Password setup is completed by the user during activation */}

              {/* Role Selection */}
              <div className="space-y-1.5">
                <label className="block text-[10px] text-zinc-500 uppercase font-bold tracking-wider">Assigned Role</label>
                <select
                  value={role}
                  onChange={(e) => setRole(e.target.value)}
                  className="input-premium bg-zinc-950 pr-8"
                >
                  <option value="ADMIN">ADMIN (Central Administrator)</option>
                  <option value="OPERATIONS">OPERATIONS (Sweeps & Reconciliation)</option>
                  <option value="AUDITOR">AUDITOR (Read-Only Compliance Logs)</option>
                </select>
              </div>

              <button
                type="submit"
                disabled={provisioning}
                className="w-full mt-2 bg-gradient-to-r from-rose-600 to-rose-500 hover:from-rose-500 hover:to-rose-400 text-black font-extrabold py-2.5 px-4 rounded-xl transition-all cursor-pointer text-center block text-[11px]"
              >
                {provisioning ? 'PROVISIONING...' : 'PROVISION STAFF'}
              </button>
            </form>
          </div>

          <div className="glass-card rounded-xl p-6 space-y-4">
            <div className="border-b border-zinc-900 pb-2 flex items-center gap-1.5">
              <KeyRound size={16} className="text-rose-500" />
              <h2 className="text-xs font-bold font-mono uppercase tracking-wider text-zinc-200">Generate Provisioning Key</h2>
            </div>
            <form onSubmit={handleGenerateStandaloneKey} className="space-y-4 text-xs font-mono">
              <div className="space-y-1.5">
                <label className="block text-[10px] text-zinc-500 uppercase font-bold tracking-wider">Target Role</label>
                <select
                  value={standaloneRole}
                  onChange={(e) => setStandaloneRole(e.target.value)}
                  className="input-premium bg-zinc-950 pr-8"
                >
                  <option value="ADMIN">ADMIN (Central Administrator)</option>
                  <option value="OPERATIONS">OPERATIONS (Sweeps & Reconciliation)</option>
                  <option value="AUDITOR">AUDITOR (Read-Only Compliance Logs)</option>
                </select>
              </div>
              <button
                type="submit"
                disabled={generatingKeyOnly}
                className="w-full mt-2 bg-gradient-to-r from-rose-600 to-rose-500 hover:from-rose-500 hover:to-rose-400 text-black font-extrabold py-2.5 px-4 rounded-xl transition-all cursor-pointer text-center block text-[11px]"
              >
                {generatingKeyOnly ? 'GENERATING...' : 'GENERATE STANDALONE KEY'}
              </button>
            </form>
          </div>
        </div>

        {/* KEYS REGISTRY TABLE */}
        <div className="glass-card rounded-xl p-6 lg:col-span-8 space-y-4">
          <div className="border-b border-zinc-900 pb-2.5 flex items-center justify-between">
            <div className="flex items-center gap-1.5">
              <KeyRound size={16} className="text-rose-500" />
              <h2 className="text-xs font-bold font-mono uppercase tracking-wider text-zinc-200">Active Admin Provisioning Keys</h2>
            </div>
            <span className="text-[9px] text-zinc-500 font-mono">{keysList.length} Keys Enrolled</span>
          </div>

          {loadingKeys ? (
            <div className="text-zinc-650 text-xs font-mono py-12 text-center">Scanning credential registries...</div>
          ) : (
            <div className="overflow-x-auto border border-zinc-900 rounded-xl bg-zinc-900/10">
              <table className="w-full text-left border-collapse font-mono text-[11px]">
                <thead>
                  <tr className="bg-zinc-900/30 border-b border-zinc-900 text-zinc-550 uppercase tracking-wider text-[8px]">
                    <th className="px-4 py-2.5">Key Hash (Salted Prefix)</th>
                    <th className="px-4 py-2.5">User reference ID</th>
                    <th className="px-4 py-2.5 text-center">Status</th>
                    <th className="px-4 py-2.5 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-zinc-900/50">
                  {keysList.map((k) => (
                    <tr key={k.id} className="hover:bg-zinc-900/25">
                      <td className="px-4 py-3 text-rose-400/80 font-bold truncate max-w-xs">{k.key_hash}</td>
                      <td className="px-4 py-3 text-zinc-400 truncate max-w-xs">
                        {k.username ? (
                          <span className="text-zinc-200 font-bold">{k.username}</span>
                        ) : (
                          <span className="text-zinc-650 italic">Unassigned (Pending Signup)</span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-center">
                        <span className={`px-2 py-0.5 rounded text-[8px] font-bold ${
                          k.is_active 
                            ? 'bg-emerald-950/20 text-emerald-400 border border-emerald-900/30' 
                            : 'bg-rose-950/20 text-rose-400 border border-rose-900/30'
                        }`}>
                          {k.is_active ? 'ACTIVE' : 'EXPIRED'}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right whitespace-nowrap space-x-1.5">
                        {k.username ? (
                          <>
                            <button
                              onClick={() => handleRegenerateKey(k.username)}
                              className="p-1 rounded bg-zinc-900 border border-zinc-800 text-zinc-450 hover:text-zinc-200 cursor-pointer"
                              title="Rotate/Regenerate Access Key"
                            >
                              <RotateCw size={11} />
                            </button>
                            <button
                              onClick={() => handleDeleteAdmin(k.username)}
                              className="p-1 rounded bg-rose-950/30 border border-rose-900/30 text-rose-450 hover:bg-rose-900/20 hover:text-rose-200 cursor-pointer"
                              title="Revoke Admin User Account"
                            >
                              <Trash2 size={11} />
                            </button>
                          </>
                        ) : (
                          <span className="text-[9px] text-zinc-650 italic">N/A (Unassigned)</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      {/* AUDIT LOGS DISPLAY */}
      <div className="glass-card rounded-xl p-6 space-y-4">
        <div className="border-b border-zinc-900 pb-2.5 flex items-center justify-between">
          <div className="flex items-center gap-1.5">
            <Activity size={16} className="text-rose-500" />
            <h2 className="text-xs font-bold font-mono uppercase tracking-wider text-zinc-200">Security Audit Logs (Zero-Trust Operations)</h2>
          </div>
          <span className="text-[9px] text-rose-500 font-mono animate-pulse">● Audit Trail Live</span>
        </div>

        {loadingLogs ? (
          <div className="text-zinc-650 text-xs font-mono py-12 text-center">Reading security logs...</div>
        ) : (
          <div className="overflow-x-auto border border-zinc-900 rounded-xl bg-[#050507]">
            <table className="w-full text-left border-collapse font-mono text-[10px]">
              <thead>
                <tr className="bg-zinc-900/30 border-b border-zinc-900 text-zinc-550 uppercase tracking-wider text-[8px]">
                  <th className="px-4.5 py-2.5">Timestamp</th>
                  <th className="px-4.5 py-2.5">User</th>
                  <th className="px-4.5 py-2.5">Role</th>
                  <th className="px-4.5 py-2.5">Action</th>
                  <th className="px-4.5 py-2.5">Details</th>
                  <th className="px-4.5 py-2.5 text-right">IP Address</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-900/50">
                {logsList.map((log) => (
                  <tr key={log.id} className="hover:bg-zinc-900/10">
                    <td className="px-4.5 py-2.5 text-zinc-550">{new Date(log.created_at).toLocaleString()}</td>
                    <td className="px-4.5 py-2.5 text-zinc-200 font-bold">{log.username}</td>
                    <td className="px-4.5 py-2.5 text-rose-400 font-semibold">{log.role}</td>
                    <td className="px-4.5 py-2.5 font-bold text-zinc-300">
                      <span className="bg-zinc-900/80 border border-zinc-800 px-1.5 py-0.5 rounded text-[9.5px]">
                        {log.action}
                      </span>
                    </td>
                    <td className="px-4.5 py-2.5 text-zinc-450 truncate max-w-sm" title={log.details || ''}>{log.details}</td>
                    <td className="px-4.5 py-2.5 text-right text-zinc-500 font-semibold">{log.ip_address || 'Internal'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

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
                <AlertTriangle size={14} />
                <span>CRITICAL: Copy this key now! It will NOT be shown again.</span>
              </p>
            </div>

            <div className="space-y-1.5">
              <label className="block text-[10px] text-zinc-550 uppercase font-bold tracking-wider">ADMIN_ACCESS_KEY</label>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={generatedKey}
                  readOnly
                  className="input-premium font-mono bg-zinc-950 text-rose-300 font-bold border-rose-950/40 select-all"
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

export default SuperAdminConsole;
