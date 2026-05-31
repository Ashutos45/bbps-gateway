import React, { useEffect, useState } from 'react';
import { 
  ScrollText, 
  Search, 
  Lock, 
  Unlock, 
  KeyRound, 
  RotateCw,
  FileText,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Eye
} from 'lucide-react';
import apiClient from '../api/apiClient';
import { useToastStore } from '../state/toastStore';
import { useAuthStore } from '../state/authStore';

interface ReportItem {
  id: string;
  title: string;
  report_type: string;
  owner_role: string;
  encrypted_preview: string;
  created_at: string;
}

export const ReportsPortal: React.FC = () => {
  const [reports, setReports] = useState<ReportItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  
  // Decryption Modal states
  const [selectedReport, setSelectedReport] = useState<ReportItem | null>(null);
  const [decryptionKey, setDecryptionKey] = useState('');
  const [decrypting, setDecrypting] = useState(false);
  const [decryptedContent, setDecryptedContent] = useState<string | null>(null);
  const [decryptionError, setDecryptionError] = useState<string | null>(null);

  const { addToast } = useToastStore();
  const { role } = useAuthStore();

  const fetchReports = async () => {
    setLoading(true);
    try {
      const response = await apiClient.get('/reports');
      // If data is returned as JSON string by apiClient's custom parser
      const parsedData = typeof response.data === 'string' ? JSON.parse(response.data) : response.data;
      setReports(parsedData);
    } catch (err: any) {
      addToast('error', `Failed to load reports: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchReports();
  }, []);

  const handleDecryptSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedReport || !decryptionKey.trim()) return;

    setDecrypting(true);
    setDecryptionError(null);
    setDecryptedContent(null);

    try {
      const response = await apiClient.post(`/reports/${selectedReport.id}/decrypt`, {
        decryption_key: decryptionKey.trim()
      });
      
      const resData = typeof response.data === 'string' ? JSON.parse(response.data) : response.data;
      if (resData.success) {
        setDecryptedContent(resData.decrypted_content);
        addToast('success', `Report decrypted successfully!`);
      } else {
        setDecryptionError(resData.message || 'Decryption failed.');
      }
    } catch (err: any) {
      let errMsg = 'Failed to decrypt report';
      if (err.response && err.response.data) {
        const errorData = typeof err.response.data === 'string' ? JSON.parse(err.response.data) : err.response.data;
        errMsg = errorData.detail || errorData.message || errMsg;
      } else if (err.message) {
        errMsg = err.message;
      }
      setDecryptionError(errMsg);
      addToast('error', `Decryption failed: ${errMsg}`);
    } finally {
      setDecrypting(false);
    }
  };

  const handleCloseModal = () => {
    setSelectedReport(null);
    setDecryptionKey('');
    setDecryptedContent(null);
    setDecryptionError(null);
  };

  // Filter reports based on search query
  const filteredReports = reports.filter(r => 
    r.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
    r.report_type.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="space-y-6">
      {/* PAGE HEADER */}
      <div className="flex flex-col md:flex-row md:justify-between md:items-center border-b border-zinc-900/60 pb-4 gap-4">
        <div>
          <h1 className="text-2xl font-extrabold font-display text-zinc-100 tracking-tight flex items-center gap-2">
            <ScrollText className="text-cyan-400 w-6 h-6 stroke-[2]" />
            Secure Reports Portal
          </h1>
          <p className="text-xs text-zinc-550 mt-1">
            PUBLIC AUDIT AND COMPLIANCE DIRECTORY. CONTENT REMAINS ENCRYPTED AT REST. DECRYPTION REQUIRES DECRYPTION KEY & AUTHORIZED ROLE.
          </p>
        </div>
        <button
          onClick={fetchReports}
          disabled={loading}
          className="border border-zinc-800 bg-zinc-900/60 hover:bg-zinc-800 text-zinc-300 rounded-lg px-3.5 py-1.5 text-[11px] cursor-pointer transition-colors font-mono flex items-center gap-1.5"
        >
          <RotateCw size={12} className={loading ? 'animate-spin' : ''} />
          <span>{loading ? 'Refreshing...' : 'Refresh Directory'}</span>
        </button>
      </div>

      {/* TOP DESK ADVISORY */}
      <div className="glass-card rounded-xl p-4 flex items-start gap-3 border-zinc-850 bg-zinc-950/20 font-mono text-[11px] leading-relaxed">
        <FileText size={16} className="text-cyan-400 flex-shrink-0 mt-0.5" />
        <div className="space-y-1">
          <span className="font-bold text-zinc-200 block uppercase">Encryption Sandbox Advisory</span>
          <p className="text-zinc-500 font-sans">
            In accordance with Zero-Trust guidelines, metadata is searchable by any visitor without authentication. 
            However, report bodies are AES-XOR encrypted. Access is guarded by RBAC role checking and symmetric key validation.
          </p>
          <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-[10px] text-cyan-400 font-mono pt-1">
            <span>Decryption Keys for Seeding:</span>
            <span>AUDIT -> <code className="text-zinc-300 bg-zinc-900 px-1 py-0.5 rounded">AUDIT_KEY_123</code></span>
            <span>TRANSACTION -> <code className="text-zinc-300 bg-zinc-900 px-1 py-0.5 rounded">OPER_KEY_123</code></span>
            <span>SECURITY -> <code className="text-zinc-300 bg-zinc-900 px-1 py-0.5 rounded">ADMIN_KEY_123</code></span>
          </div>
        </div>
      </div>

      {/* SEARCH AND DIRECTORY VIEW */}
      <div className="space-y-4">
        <div className="relative max-w-md">
          <span className="absolute inset-y-0 left-0 pl-3.5 flex items-center text-zinc-600">
            <Search size={14} />
          </span>
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search reports by title, category, or owner role..."
            className="input-premium pl-10 text-xs font-mono"
          />
        </div>

        {loading && reports.length === 0 ? (
          <div className="text-zinc-650 text-xs font-mono py-16 text-center flex items-center justify-center gap-2">
            <RotateCw className="animate-spin" size={16} />
            Scanning secure reports directory...
          </div>
        ) : filteredReports.length === 0 ? (
          <div className="text-zinc-500 text-xs font-sans py-16 border border-dashed border-zinc-900 rounded-xl text-center bg-zinc-950/10 flex flex-col items-center justify-center gap-2.5">
            <ScrollText size={28} className="text-zinc-700" />
            <span>No reports found matching your criteria.</span>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 font-mono">
            {filteredReports.map((report) => (
              <div 
                key={report.id} 
                className="glass-card rounded-xl p-5 flex flex-col justify-between space-y-4 border-zinc-800/80 bg-zinc-950/40 hover:border-zinc-850 hover:bg-zinc-900/10 transition-all group"
              >
                <div className="space-y-2">
                  <div className="flex justify-between items-start">
                    <span className={`px-2 py-0.5 text-[8px] font-bold rounded border ${
                      report.report_type === 'SECURITY' 
                        ? 'bg-rose-950/20 text-rose-400 border-rose-900/30'
                        : report.report_type === 'AUDIT'
                        ? 'bg-purple-950/20 text-purple-400 border-purple-900/30'
                        : 'bg-amber-950/20 text-amber-400 border-amber-900/30'
                    }`}>
                      {report.report_type}
                    </span>
                    <span className="text-[9px] text-zinc-600">{new Date(report.created_at).toLocaleDateString()}</span>
                  </div>
                  <h3 className="font-bold text-zinc-200 text-xs group-hover:text-cyan-400 transition-colors pt-1">
                    {report.title}
                  </h3>
                  <div className="text-[10px] text-zinc-500 font-sans leading-relaxed pt-1.5">
                    Clearance Required: <span className="font-mono font-bold text-cyan-500">{report.owner_role}</span>
                  </div>
                </div>

                <div className="space-y-3.5 pt-3 border-t border-zinc-900/60">
                  <div className="bg-[#050507] border border-zinc-900/80 rounded p-2.5 text-[9px] text-zinc-650 flex items-center justify-between">
                    <span className="font-mono select-none">PREVIEW: {report.encrypted_preview}</span>
                    <Lock size={11} className="text-rose-500" />
                  </div>

                  <button
                    onClick={() => {
                      setSelectedReport(report);
                      setDecryptionKey('');
                      setDecryptedContent(null);
                      setDecryptionError(null);
                    }}
                    className="w-full bg-zinc-900/80 hover:bg-zinc-800 hover:text-cyan-400 text-zinc-300 font-mono text-[10px] py-2 rounded-lg border border-zinc-800 transition-all flex items-center justify-center gap-1.5 cursor-pointer"
                  >
                    <Eye size={12} />
                    <span>Decrypt & Inspect</span>
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* DECRYPTION DIALOG MODAL */}
      {selectedReport && (
        <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4 font-mono text-xs">
          <div className="glass-card rounded-xl p-6 border-zinc-800 bg-[#09090b] max-w-lg w-full space-y-4 shadow-xl">
            
            {/* Header */}
            <div className="flex justify-between items-start border-b border-zinc-900 pb-3">
              <div>
                <h3 className="font-display font-bold text-zinc-200 text-sm">Secure Report Sweep</h3>
                <span className="text-[10px] text-zinc-550 block mt-0.5">Decrypting: {selectedReport.title}</span>
              </div>
              <button 
                onClick={handleCloseModal}
                className="text-zinc-500 hover:text-zinc-300 font-mono text-[10px] cursor-pointer"
              >
                Close
              </button>
            </div>

            {/* Advisory Info */}
            <div className="grid grid-cols-2 gap-3 text-[10px] bg-[#050507]/40 border border-zinc-900 p-2.5 rounded-lg text-zinc-500">
              <div>
                <span>OWNER ROLE CLEARANCE</span>
                <span className="block font-bold text-cyan-400 mt-0.5">{selectedReport.owner_role}</span>
              </div>
              <div>
                <span>YOUR ACTIVE IDENTITY ROLE</span>
                <span className="block font-bold text-zinc-300 mt-0.5">{role}</span>
              </div>
            </div>

            {/* Main Decrypted Output Console / Form */}
            {!decryptedContent ? (
              <form onSubmit={handleDecryptSubmit} className="space-y-4">
                <div className="space-y-1.5">
                  <label className="block text-[9px] text-zinc-550 uppercase font-bold tracking-wider">Provide Decryption Key</label>
                  <div className="relative">
                    <span className="absolute inset-y-0 left-0 pl-3 flex items-center text-zinc-650">
                      <KeyRound size={12} />
                    </span>
                    <input
                      type="text"
                      value={decryptionKey}
                      onChange={(e) => setDecryptionKey(e.target.value)}
                      placeholder="Enter symmetric key (e.g. AUDIT_KEY_123)..."
                      className="input-premium pl-9 font-mono text-xs"
                      required
                      autoFocus
                    />
                  </div>
                </div>

                {decryptionError && (
                  <div className="bg-rose-950/20 border border-rose-900/40 text-rose-400 p-3 rounded-lg text-[10px] flex items-start gap-2 leading-relaxed">
                    <XCircle size={13} className="flex-shrink-0 mt-0.5" />
                    <div>
                      <span className="font-bold">Authorization Failure:</span> {decryptionError}
                    </div>
                  </div>
                )}

                <div className="flex justify-end gap-2 text-[10px] font-bold">
                  <button
                    type="button"
                    onClick={handleCloseModal}
                    className="border border-zinc-850 hover:bg-zinc-900 text-zinc-400 hover:text-zinc-200 py-2 px-4 rounded-lg cursor-pointer"
                  >
                    CANCEL
                  </button>
                  <button
                    type="submit"
                    disabled={decrypting}
                    className="bg-cyan-600 hover:bg-cyan-500 text-black py-2 px-4 rounded-lg cursor-pointer flex items-center gap-1.5"
                  >
                    {decrypting ? <RotateCw className="animate-spin" size={10} /> : <Unlock size={10} />}
                    <span>DECRYPT BODY</span>
                  </button>
                </div>
              </form>
            ) : (
              <div className="space-y-4 animate-fade-in">
                <div className="bg-emerald-950/20 border border-emerald-900/40 text-emerald-400 p-3 rounded-lg text-[10px] flex items-center gap-1.5 font-bold">
                  <CheckCircle size={13} />
                  <span>Symmetric Decryption Handshake Succeeded.</span>
                </div>

                <div className="space-y-1.5">
                  <label className="block text-[9px] text-zinc-550 uppercase font-bold tracking-wider">Cleartext Decrypted Content</label>
                  <pre className="bg-[#050507] border border-zinc-900 p-4 rounded-lg text-[10.5px] text-cyan-400/90 overflow-x-auto whitespace-pre-wrap font-mono leading-relaxed select-all">
                    {decryptedContent}
                  </pre>
                </div>

                <div className="flex justify-end pt-2">
                  <button
                    type="button"
                    onClick={handleCloseModal}
                    className="bg-cyan-600 hover:bg-cyan-500 text-black py-2 px-6 rounded-lg cursor-pointer font-bold"
                  >
                    DISMISS REPORT
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default ReportsPortal;
