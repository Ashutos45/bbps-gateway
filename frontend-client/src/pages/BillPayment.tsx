import React, { useState, useEffect } from 'react';
import { usePaymentStore } from '../state/paymentStore';
import { useCacheStore } from '../state/cacheStore';
import { useReconciliationStore } from '../state/reconciliationStore';
import { queryBillers } from '../cache/db';
import { BillerListVirtualized } from '../components/BillerListVirtualized';
import { BillerSearch } from '../components/BillerSearch';
import { BillFetchForm } from '../components/BillFetchForm';
import { PaymentForm } from '../components/PaymentForm';
import { TransactionTracker } from '../components/TransactionTracker';
import { FavoriteBillers } from '../components/FavoriteBillers';
import { usePolling } from '../hooks/usePolling';
import { Biller } from '../types';
import { CreditCard, Search, HelpCircle, User, Star } from 'lucide-react';

export const BillPayment: React.FC = () => {
  const {
    activeBiller,
    activeBillDetails,
    billFetchStatus,
    paymentStatus,
    paymentError,
    paymentResponse,
    currentTransaction,
    favoriteBillers,
    favoriteBillersLoading,
    setActiveBiller,
    resetBillFetch,
    resetPayment,
    fetchBill,
    payBill,
    loadFavoriteBillers,
    deleteFavoriteBiller,
  } = usePaymentStore();

  const { categories, regions, checkCacheStatus } = useCacheStore();
  const { loadOneView, transactions } = useReconciliationStore();

  const [search, setSearch] = useState('');
  const [category, setCategory] = useState('All');
  const [region, setRegion] = useState('All');

  const [filteredBillers, setFilteredBillers] = useState<Biller[]>([]);
  const [customerId, setCustomerId] = useState('cust123');

  // INITIAL LOAD
  useEffect(() => {
    checkCacheStatus();
    loadFavoriteBillers(customerId);
  }, [checkCacheStatus, loadFavoriteBillers, customerId]);

  // FETCH FILTERED OPERATORS
  useEffect(() => {
    const fetchFiltered = async () => {
      try {
        const normalizedCategory = category === 'All' ? '' : category;
        const normalizedRegion = region === 'All' ? '' : region;

        const result = await queryBillers(
          search.trim(),
          normalizedCategory.trim(),
          normalizedRegion.trim(),
          0,
          200
        );

        if (result && Array.isArray(result.billers)) {
          setFilteredBillers(result.billers);
        } else {
          setFilteredBillers([]);
        }
      } catch (err) {
        console.error('Failed loading billers:', err);
        setFilteredBillers([]);
      }
    };

    fetchFiltered();
  }, [search, category, region]);

  // SELECT BILLER
  const handleSelectBiller = (biller: Biller) => {
    setActiveBiller(biller);
    resetPayment();
  };

  // FETCH BILL
  const handleFetchBillSubmit = async (params: {
    customerId: string;
    customer: any;
    authenticators: any[];
    paymentAmount: string;
  }) => {
    try {
      await fetchBill(
        params.customerId,
        params.authenticators,
        params.customer
      );
    } catch (e) {
      console.error(e);
    }
  };

  // PAYMENT
  const handlePaymentSubmit = async (params: {
    paymentMethod: string;
    cardholderName: string;
    paymentAmount: string;
    paymentType: string;
  }) => {
    if (!activeBillDetails) return;

    try {
      await payBill({
        customerId,
        customer:
          activeBillDetails.billlist?.[0]?.customer || {
            firstname:
              activeBillDetails.billlist?.[0]?.customer_name?.split(' ')[0] ||
              'Rahul',
            lastname:
              activeBillDetails.billlist?.[0]?.customer_name?.split(' ')[1] ||
              'Sharma',
            mobile: '9999999999',
          },
        validationId: activeBillDetails.validationid,
        paymentAmount: params.paymentAmount,
        paymentType: params.paymentType,
        paymentMethod: params.paymentMethod,
        cardholderName: params.cardholderName,
        authenticators: activeBillDetails.authenticators,
      });

      loadFavoriteBillers(customerId);
      loadOneView(customerId);
    } catch (e) {
      console.warn(
        'Payment executed with errors, tracker will manage recovery.',
        e
      );
    }
  };

  // QUICK PAY
  const handleQuickPaySelect = (fav: any) => {
    const selected =
      filteredBillers.find((b) => b.biller_id === fav.biller_id) || {
        biller_id: fav.biller_id,
        biller_name: fav.short_name,
        category: 'Utility',
        region: 'National',
      };

    setActiveBiller(selected);
    resetPayment();

    const customer = {
      firstname: 'Rahul',
      lastname: 'Sharma',
      mobile: '9999999999',
    };

    fetchBill(customerId, fav.authenticators, customer);
  };

  // CLEAR
  const handleClearBiller = () => {
    setActiveBiller(null);
    resetPayment();
  };

  // POLLING
  const shouldPoll =
    currentTransaction?.transaction_state === 'AMBIGUOUS_TIMEOUT';

  usePolling(async () => {
    if (!shouldPoll || !currentTransaction?.trace_id) return true;

    try {
      await loadOneView(customerId);

      const matched = transactions.find(
        (t) => t.trace_id === currentTransaction.trace_id
      );

      if (
        matched &&
        matched.transaction_state !== 'AMBIGUOUS_TIMEOUT'
      ) {
        usePaymentStore.setState({
          currentTransaction: {
            ...currentTransaction,
            transaction_state: matched.transaction_state,
            updated_at:
              matched.updated_at || new Date().toISOString(),
            response_payload: matched.response_payload,
          },
        });

        return true;
      }
    } catch (e) {
      console.error('Error polling transaction status', e);
    }

    return false;
  }, shouldPoll ? 2000 : null);

  const handleRefreshTracker = async () => {
    if (!currentTransaction?.trace_id) return;

    await loadOneView(customerId);

    const matched = transactions.find(
      (t) => t.trace_id === currentTransaction.trace_id
    );

    if (matched) {
      usePaymentStore.setState({
        currentTransaction: {
          ...currentTransaction,
          transaction_state: matched.transaction_state,
          updated_at:
            matched.updated_at || new Date().toISOString(),
          response_payload: matched.response_payload,
        },
      });
    }
  };

  return (
    <div className="space-y-6">
      {/* HEADER */}
      <div className="flex flex-col md:flex-row md:justify-between md:items-center border-b border-zinc-900/60 pb-4 gap-4">
        <div>
          <h1 className="text-2xl font-extrabold font-display text-zinc-100 tracking-tight flex items-center gap-2">
            <CreditCard className="text-cyan-400 w-6 h-6 stroke-[2]" />
            Submit Bill Payment
          </h1>
          <p className="text-xs text-zinc-500 mt-1">
            INITIATE CLIENT VALIDATIONS, EXECUTE TRANSACTIONS, AND TRACK ASYNC STATE RECOVERIES
          </p>
        </div>
      </div>

      {/* SAVED FAVORITES */}
      <div className="space-y-3.5">
        <span className="block text-[10px] font-mono font-bold text-zinc-500 uppercase tracking-widest flex items-center gap-1.5">
          <Star size={11} className="text-amber-500 fill-amber-500/20" />
          SAVED OPERATOR SHORTCUTS (QUICK PAY)
        </span>
        <FavoriteBillers
          favorites={favoriteBillers}
          loading={favoriteBillersLoading}
          onSelect={handleQuickPaySelect}
          onDelete={(id) => deleteFavoriteBiller(customerId, id)}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* LEFT COLUMN: DIRECTORY & SEARCH */}
        <div className="lg:col-span-4 space-y-4">
          <div className="glass-card rounded-xl p-5 border-zinc-800/80 bg-zinc-950/40">
            <span className="text-xs font-display font-extrabold text-zinc-200 mb-4 block flex items-center gap-2">
              <Search size={14} className="text-cyan-400" />
              Operator Search Directory
            </span>

            <BillerSearch
              search={search}
              category={category}
              region={region}
              categories={['All', ...categories]}
              regions={['All', ...regions]}
              onSearchChange={setSearch}
              onCategoryChange={setCategory}
              onRegionChange={setRegion}
              onClearFilters={() => {
                setSearch('');
                setCategory('All');
                setRegion('All');
              }}
            />
          </div>

          <BillerListVirtualized
            billers={filteredBillers}
            onSelectBiller={handleSelectBiller}
            selectedBillerId={activeBiller?.biller_id}
            height={312}
          />
        </div>

        {/* RIGHT COLUMN: GUIDED FORM PANEL */}
        <div className="lg:col-span-8 space-y-6">
          {!activeBiller ? (
            <div className="border border-dashed border-zinc-900 rounded-xl p-16 text-center text-zinc-500 font-sans text-xs bg-zinc-950/10 flex flex-col items-center justify-center gap-3">
              <HelpCircle size={32} className="text-zinc-700" />
              <div className="max-w-xs leading-relaxed">
                Select an operator biller from the search directory on the left to start the validation workflow.
              </div>
            </div>
          ) : (
            <div className="space-y-6">
              {/* SELECTED OPERATOR PANEL */}
              <div className="glass-card rounded-xl px-5 py-3.5 flex justify-between items-center border-zinc-800/80 bg-zinc-950/40 animate-fade-in">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-lg bg-emerald-950/20 border border-emerald-900/20 flex items-center justify-center text-emerald-400">
                    <User size={15} />
                  </div>
                  <div>
                    <span className="text-[9px] text-emerald-400 font-mono block font-bold uppercase tracking-wider">
                      ACTIVE SELECTED OPERATOR
                    </span>
                    <span className="text-sm font-bold text-zinc-200 block font-display">
                      {activeBiller.biller_name}
                    </span>
                  </div>
                </div>

                <button
                  onClick={handleClearBiller}
                  className="text-xs text-zinc-550 hover:text-zinc-350 transition-colors font-mono cursor-pointer underline underline-offset-2"
                >
                  Clear Selection
                </button>
              </div>

              {/* STEP 1: FETCH BILL */}
              {billFetchStatus !== 'SUCCESS' && (
                <BillFetchForm
                  biller={activeBiller}
                  customerId={customerId}
                  onCustomerIdChange={setCustomerId}
                  onSubmit={handleFetchBillSubmit}
                  loading={billFetchStatus === 'LOADING'}
                />
              )}

              {/* STEP 1 ERROR MESSAGE */}
              {billFetchStatus === 'ERROR' && (
                <div className="bg-rose-950/20 border border-rose-900/40 text-rose-450 p-4.5 rounded-xl font-mono text-xs animate-fade-in leading-relaxed flex items-start gap-2.5">
                  <span className="text-rose-400 font-bold block mt-0.5">ERROR:</span>
                  <div>
                    <span className="font-bold block">Bill Fetch Validation Failed</span>
                    <p className="mt-1.5 text-rose-350">
                      {paymentError || 'The downstream provider did not return any outstanding balance for this account.'}
                    </p>
                  </div>
                </div>
              )}

              {/* STEP 2: PAYMENT FORM */}
              {billFetchStatus === 'SUCCESS' &&
                activeBillDetails &&
                paymentStatus !== 'SUCCESS' &&
                paymentStatus !== 'ERROR' && (
                  <PaymentForm
                    biller={activeBiller}
                    billDetails={activeBillDetails}
                    onSubmit={handlePaymentSubmit}
                    loading={paymentStatus === 'PENDING'}
                    onCancel={resetBillFetch}
                  />
                )}

              {/* STEP 3: TRANSACTION TRACKER */}
              {(paymentStatus === 'SUCCESS' ||
                paymentStatus === 'ERROR' ||
                currentTransaction) && (
                <TransactionTracker
                  transaction={currentTransaction}
                  pollingActive={shouldPoll}
                  onRefresh={handleRefreshTracker}
                />
              )}

              {/* SUCCESS RECEIPT STATUS */}
              {paymentStatus === 'SUCCESS' &&
                paymentResponse && (
                  <div className="bg-emerald-950/20 border border-emerald-900/40 text-emerald-400 p-5.5 rounded-xl font-mono text-xs space-y-3 animate-fade-in">
                    <div className="font-extrabold text-sm flex items-center gap-1.5 font-display uppercase tracking-wide">
                      ✓ Transaction Settled Successfully
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-[10px] pt-1.5 border-t border-emerald-900/20">
                      <div>
                        PAYMENT REF ID:{' '}
                        <span className="text-zinc-200 font-bold select-all">
                          {paymentResponse.payment_reference}
                        </span>
                      </div>

                      <div>
                        SETTLEMENT DATE:{' '}
                        <span className="text-zinc-200 font-bold">
                          {paymentResponse.payment_date}
                        </span>
                      </div>

                      <div>
                        AMOUNT DEBITED:{' '}
                        <span className="text-zinc-200 font-extrabold font-sans">
                          ₹{paymentResponse.debit_amount}
                        </span>
                      </div>

                      <div>
                        COU STATUS CODE:{' '}
                        <span className="text-emerald-350 font-bold uppercase">
                          {paymentResponse.status}
                        </span>
                      </div>
                    </div>
                  </div>
                )}

              {/* FAILURE ERROR DIALOG */}
              {paymentStatus === 'ERROR' &&
                paymentError &&
                !shouldPoll && (
                  <div className="bg-rose-950/20 border border-rose-900/40 text-rose-450 p-4.5 rounded-xl font-mono text-xs animate-fade-in">
                    <span className="font-extrabold text-sm block">
                      ✗ Transaction Execution Rejected
                    </span>

                    <p className="mt-2 leading-relaxed text-rose-350">
                      {paymentError}
                    </p>
                  </div>
                )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default BillPayment;