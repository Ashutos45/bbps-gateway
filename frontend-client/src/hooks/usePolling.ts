import { useEffect, useRef } from 'react';

/**
 * A custom hook to poll an asynchronous operation safely.
 * @param callback A function returning a boolean or a promise resolving to boolean.
 *                 If it returns true, polling is stopped.
 * @param interval The delay between ticks in milliseconds. Pass null to pause polling.
 */
export function usePolling(
  callback: () => Promise<boolean> | boolean,
  interval: number | null
) {
  const savedCallback = useRef(callback);

  useEffect(() => {
    savedCallback.current = callback;
  }, [callback]);

  useEffect(() => {
    if (interval === null) return;

    let timeoutId: any;
    let isCancelled = false;

    const runPoll = async () => {
      if (isCancelled) return;
      
      try {
        const shouldStop = await savedCallback.current();
        if (shouldStop) {
          isCancelled = true;
          return;
        }
      } catch (err) {
        console.error('Error encountered during polling execution', err);
      }

      if (!isCancelled) {
        timeoutId = setTimeout(runPoll, interval);
      }
    };

    timeoutId = setTimeout(runPoll, interval);

    return () => {
      isCancelled = true;
      clearTimeout(timeoutId);
    };
  }, [interval]);
}
export default usePolling;
