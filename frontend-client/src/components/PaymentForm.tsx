import React, { useState } from 'react';
import { CreditCard, Landmark, CheckCircle, ChevronRight, X } from 'lucide-react';
import { Biller } from '../types';

interface PaymentFormProps {
  biller: Biller;
  billDetails: any; 
  onSubmit: (params: {
    paymentMethod: string;
    cardholderName: string;
    paymentAmount: string;
    paymentType: string;
  }) => void;
  loading: boolean;
  onCancel: () => void;
}

export const PaymentForm: React.FC<PaymentFormProps> = ({
  biller,
  billDetails,
  onSubmit,
  loading,
  onCancel,
}) => {
  const [paymentMethod, setPaymentMethod] = useState('DebitCard');
  const [cardholderName, setCardholderName] = useState('Rahul Sharma');
  const [paymentType, setPaymentType] = useState('billpay');

  const bill = billDetails.billlist?.[0];
  const originalAmount = bill?.billamount || billDetails.payment_amount || '920.00';
  const [amount, setAmount] = useState(originalAmount);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!amount || parseFloat(amount) <= 0) return;

    onSubmit({
      paymentMethod,
      cardholderName,
      paymentAmount: amount,
      paymentType,
    });
  };

  const getMethodIcon = (method: string) => {
    switch (method) {
      case 'DebitCard':
      case 'CreditCard':
        return <CreditCard size={14} className="text-cyan-400" />;
      case 'NetBanking':
      case 'UPI':
        return <Landmark size={14} className="text-cyan-400" />;
      default:
        return <CreditCard size={14} className="text-cyan-400" />;
    }
  };

  return (
    <form onSubmit={handleSubmit} className="glass-card rounded-xl p-6 space-y-5 border-zinc-800/80 bg-zinc-950/40 animate-fade-in">
      <div className="border-b border-zinc-900 pb-3 mb-2 flex justify-between items-start">
        <div>
          <h3 className="text-sm font-display font-bold text-zinc-200">
            Step 2: Submit Payment Transaction
          </h3>
          <p className="text-[10px] text-zinc-550 mt-1 font-mono">
            AUTHORIZE DEBIT AGAINST VALIDATION: <span className="text-cyan-450 font-bold select-all">{billDetails.validationid}</span>
          </p>
        </div>
        <button
          type="button"
          onClick={onCancel}
          className="text-zinc-400 hover:text-zinc-200 border border-zinc-800 hover:border-zinc-700 rounded-lg p-1.5 transition-colors cursor-pointer"
        >
          <X size={14} />
        </button>
      </div>

      {/* Bill Overview Card */}
      <div className="bg-[#09090b]/60 border border-zinc-900 rounded-xl p-4 font-mono text-xs space-y-2.5 shadow-sm">
        <div className="flex justify-between items-center text-zinc-500">
          <span>Customer Account:</span>
          <span className="text-zinc-350 font-bold font-sans">{bill?.customer_name || 'Rahul Sharma'}</span>
        </div>
        <div className="flex justify-between items-center text-zinc-500">
          <span>Bill Ref Number:</span>
          <span className="text-zinc-350 font-bold select-all">{bill?.billnumber || 'BILL-10023'}</span>
        </div>
        <div className="flex justify-between items-center text-zinc-500">
          <span>Bill Period Cycle:</span>
          <span className="text-zinc-350">{bill?.billperiod || 'Current Month'}</span>
        </div>
        <div className="flex justify-between items-center border-t border-zinc-900/60 pt-2.5 mt-2 text-zinc-450">
          <span className="font-extrabold">Owed Amount:</span>
          <span className="font-extrabold text-sm text-emerald-400 font-display">₹{originalAmount}</span>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Payment Type */}
        <div>
          <label className="block text-[10px] font-mono font-bold text-zinc-550 mb-1.5 uppercase tracking-wider">Payment Route Type</label>
          <select
            value={paymentType}
            onChange={(e) => setPaymentType(e.target.value)}
            className="input-premium appearance-none bg-zinc-950 font-mono"
          >
            <option value="billpay">Bill Pay (Standard)</option>
            <option value="instapay">Instapay (Immediate)</option>
            <option value="adhoc">Adhoc Payment</option>
          </select>
        </div>

        {/* Payment Method */}
        <div>
          <label className="block text-[10px] font-mono font-bold text-zinc-550 mb-1.5 uppercase tracking-wider">Payment Method Instrument</label>
          <div className="relative">
            <select
              value={paymentMethod}
              onChange={(e) => setPaymentMethod(e.target.value)}
              className="input-premium appearance-none bg-zinc-950 font-mono pl-9"
            >
              <option value="DebitCard">Debit Card</option>
              <option value="CreditCard">Credit Card</option>
              <option value="NetBanking">Net Banking</option>
              <option value="UPI">UPI (Unified Payments Interface)</option>
            </select>
            <span className="absolute inset-y-0 left-0 pl-3 flex items-center text-zinc-500 pointer-events-none">
              {getMethodIcon(paymentMethod)}
            </span>
          </div>
        </div>

        {/* Cardholder / Account Name */}
        <div>
          <label className="block text-[10px] font-mono font-bold text-zinc-550 mb-1.5 uppercase tracking-wider">Cardholder / Account Name</label>
          <input
            type="text"
            value={cardholderName}
            onChange={(e) => setCardholderName(e.target.value)}
            className="input-premium"
            required
          />
        </div>

        {/* Settlement Amount */}
        <div>
          <label className="block text-[10px] font-mono font-bold text-zinc-550 mb-1.5 uppercase tracking-wider">Settlement Amount (₹)</label>
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
        <span className="text-[9px] text-zinc-600 font-mono uppercase">Secured by BobCOU banking encryption rules.</span>
        
        <button
          type="submit"
          disabled={loading}
          className="flex items-center space-x-2 bg-gradient-to-r from-cyan-600 to-cyan-500 hover:from-cyan-500 hover:to-cyan-400 disabled:from-zinc-900 disabled:to-zinc-900 disabled:text-zinc-650 text-black font-display text-xs font-black px-5 py-2.5 rounded-lg transition-all duration-150 cursor-pointer shadow-md shadow-cyan-950/20"
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
              <span className="font-mono text-[10px] uppercase font-bold tracking-wider">Submitting to gateway...</span>
            </>
          ) : (
            <span className="flex items-center gap-1 uppercase tracking-wider font-extrabold text-[10px]">
              <CheckCircle size={12} />
              Authorize & Settle
              <ChevronRight size={12} />
            </span>
          )}
        </button>
      </div>
    </form>
  );
};

export default PaymentForm;
