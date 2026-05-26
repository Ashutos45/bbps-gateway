import React, { useState } from 'react';
import { UserCheck, Sparkles, AlertCircle } from 'lucide-react';
import { Biller, Authenticator, Customer } from '../types';

interface BillFetchFormProps {
  biller: Biller;
  customerId: string;
  onCustomerIdChange: (val: string) => void;
  onSubmit: (params: {
    customerId: string;
    customer: Customer;
    authenticators: Authenticator[];
    paymentAmount: string;
  }) => void;
  loading: boolean;
}

export const BillFetchForm: React.FC<BillFetchFormProps> = ({
  biller,
  customerId,
  onCustomerIdChange,
  onSubmit,
  loading,
}) => {
  const [firstName, setFirstName] = useState('John');
  const [lastName, setLastName] = useState('Doe');
  const [mobile, setMobile] = useState('9999999999');
  const [authVal, setAuthVal] = useState('123456789');
  const [amount, setAmount] = useState('920.00');

  const getAuthLabel = (category: string) => {
    switch (category) {
      case 'Electricity':
        return 'Consumer No';
      case 'DTH':
        return 'Subscriber ID';
      case 'Mobile Postpaid':
      case 'Mobile Prepaid':
        return 'Mobile Number';
      case 'Water':
        return 'Connection No';
      case 'Gas':
      case 'LPG Gas':
        return 'Customer Account No';
      default:
        return 'Account ID';
    }
  };

  const getAuthPlaceholder = (category: string) => {
    switch (category) {
      case 'Electricity':
        return 'e.g. 100234567';
      case 'DTH':
        return 'e.g. 300456123';
      case 'Mobile Postpaid':
      case 'Mobile Prepaid':
        return 'e.g. 9876543210';
      default:
        return 'e.g. ACC102345';
    }
  };

  const authLabel = getAuthLabel(biller.category);
  const authPlaceholder = getAuthPlaceholder(biller.category);

  // Auto fill helper for demonstration purposes
  const handleQuickFill = () => {
    setFirstName('Rahul');
    setLastName('Sharma');
    setMobile('9876543210');
    setAuthVal('5500104928');
    setAmount('1250.00');
    onCustomerIdChange('cust123');
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!authVal.trim()) return;

    const authenticators: Authenticator[] = [
      {
        seq: '1',
        parameter_name: authLabel,
        value: authVal,
      },
    ];

    const customer: Customer = {
      firstname: firstName,
      lastname: lastName,
      mobile,
    };

    onSubmit({
      customerId,
      customer,
      authenticators,
      paymentAmount: amount,
    });
  };

  return (
    <form onSubmit={handleSubmit} className="glass-card rounded-xl p-6 space-y-5 border-zinc-800/80 bg-zinc-950/40">
      <div className="border-b border-zinc-900 pb-3 mb-2 flex justify-between items-start flex-wrap gap-2">
        <div>
          <h3 className="text-sm font-display font-bold text-zinc-200">
            Step 1: Authenticate Customer & Fetch Bill
          </h3>
          <p className="text-[10px] text-zinc-550 mt-1 font-mono">
            PROVIDE CLIENT ACCOUNT DETAILS FOR OPERATOR: <span className="text-cyan-400 font-semibold">{biller.biller_name}</span>
          </p>
        </div>
        
        {/* Quick Fill Preset */}
        <button
          type="button"
          onClick={handleQuickFill}
          className="bg-cyan-950/30 hover:bg-cyan-950/50 border border-cyan-800/30 text-cyan-400 font-mono text-[9px] font-bold px-2 py-1 rounded transition-colors flex items-center gap-1 cursor-pointer"
        >
          <Sparkles size={9} />
          <span>QUICK FILL DEMO PRESETS</span>
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Customer ID */}
        <div>
          <label className="block text-[10px] font-mono font-bold text-zinc-550 mb-1.5 uppercase tracking-wider">Customer Ref ID</label>
          <input
            type="text"
            value={customerId}
            onChange={(e) => onCustomerIdChange(e.target.value)}
            className="input-premium font-mono"
            required
          />
          <span className="text-[9px] text-zinc-600 block mt-1 font-mono">Operations customer profile</span>
        </div>

        {/* Dynamic Authenticator Input */}
        <div>
          <label className="block text-[10px] font-mono font-bold text-zinc-550 mb-1.5 uppercase tracking-wider">{authLabel}</label>
          <input
            type="text"
            value={authVal}
            onChange={(e) => setAuthVal(e.target.value)}
            placeholder={authPlaceholder}
            className="input-premium font-mono"
            required
          />
          <span className="text-[9px] text-zinc-600 block mt-1 font-mono">Official BBPS parameter validation</span>
        </div>

        {/* First Name */}
        <div>
          <label className="block text-[10px] font-mono font-bold text-zinc-550 mb-1.5 uppercase tracking-wider">Customer First Name</label>
          <input
            type="text"
            value={firstName}
            onChange={(e) => setFirstName(e.target.value)}
            className="input-premium"
            required
          />
        </div>

        {/* Last Name */}
        <div>
          <label className="block text-[10px] font-mono font-bold text-zinc-550 mb-1.5 uppercase tracking-wider">Customer Last Name</label>
          <input
            type="text"
            value={lastName}
            onChange={(e) => setLastName(e.target.value)}
            className="input-premium"
            required
          />
        </div>

        {/* Mobile Number */}
        <div>
          <label className="block text-[10px] font-mono font-bold text-zinc-550 mb-1.5 uppercase tracking-wider">Mobile Number</label>
          <input
            type="tel"
            value={mobile}
            onChange={(e) => setMobile(e.target.value)}
            className="input-premium font-mono"
            required
          />
        </div>

        {/* Custom Bill Amount */}
        <div>
          <label className="block text-[10px] font-mono font-bold text-zinc-550 mb-1.5 uppercase tracking-wider">Simulated Balance (₹)</label>
          <input
            type="number"
            step="0.01"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            className="input-premium font-mono"
            required
          />
        </div>
      </div>

      <div className="flex justify-between items-center pt-2 border-t border-zinc-900/60 mt-2">
        <div className="flex items-center gap-1 text-[9px] text-zinc-550 font-mono">
          <AlertCircle size={10} className="text-zinc-600" />
          <span>Zero payload complexity. Intelligent defaults active.</span>
        </div>

        <button
          type="submit"
          disabled={loading}
          className="flex items-center space-x-2 bg-gradient-to-r from-cyan-600 to-cyan-500 hover:from-cyan-500 hover:to-cyan-400 disabled:from-zinc-900 disabled:to-zinc-900 disabled:text-zinc-650 text-black font-display text-xs font-black px-4.5 py-2.5 rounded-lg transition-all duration-150 cursor-pointer shadow-md shadow-cyan-950/20"
        >
          {loading ? (
            <>
              <svg
                className="animate-spin -ml-1 mr-2 h-4.5 w-4.5 text-black"
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
              >
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                ></circle>
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                ></path>
              </svg>
              <span className="font-mono text-[10px] uppercase font-bold tracking-wider">Verifying authenticators...</span>
            </>
          ) : (
            <span className="flex items-center gap-1 uppercase tracking-wider font-extrabold text-[10px]">
              <UserCheck size={12} />
              Fetch Bill Details
            </span>
          )}
        </button>
      </div>
    </form>
  );
};

export default BillFetchForm;
