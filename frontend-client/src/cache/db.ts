import { unzipSync } from 'fflate';
import apiClient from '../api/apiClient';
import { Biller } from '../types';

export function openDB(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open('bbps-cache-db', 1);
    request.onupgradeneeded = () => {
      const db = request.result;
      if (!db.objectStoreNames.contains('billers')) {
        const store = db.createObjectStore('billers', { keyPath: 'biller_id' });
        store.createIndex('category', 'category', { unique: false });
        store.createIndex('region', 'region', { unique: false });
        store.createIndex('biller_name', 'biller_name', { unique: false });
      }
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

export async function clearCache(): Promise<void> {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction('billers', 'readwrite');
    const store = tx.objectStore('billers');
    const req = store.clear();
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(req.error);
  });
}

export async function saveBillersInChunks(billers: Biller[], chunkSize: number = 20): Promise<void> {
  const db = await openDB();
  for (let i = 0; i < billers.length; i += chunkSize) {
    const chunk = billers.slice(i, i + chunkSize);
    await new Promise<void>((resolve, reject) => {
      const tx = db.transaction('billers', 'readwrite');
      const store = tx.objectStore('billers');
      chunk.forEach((biller) => store.put(biller));
      tx.oncomplete = () => resolve();
      tx.onerror = () => reject(tx.error);
    });
    // Yield CPU time to allow main thread processing and keep UI responsive
    await new Promise((resolve) => setTimeout(resolve, 10));
  }
}

export async function queryBillers(
  search: string,
  category: string,
  region: string,
  offset: number,
  limit: number
): Promise<{ billers: Biller[]; total: number }> {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction('billers', 'readonly');
    const store = tx.objectStore('billers');
    const request = store.openCursor();

    const filtered: Biller[] = [];
    let total = 0;
    const searchLower = search ? search.toLowerCase() : '';

    request.onsuccess = (event) => {
      const cursor = (event.target as IDBRequest).result as IDBCursorWithValue;
      if (cursor) {
        const b = cursor.value as Biller;
        const matchesSearch =
          !searchLower ||
          b.biller_name.toLowerCase().includes(searchLower) ||
          b.biller_id.toLowerCase().includes(searchLower);
        const matchesCategory = !category || b.category === category;
        const matchesRegion = !region || b.region === region;

        if (matchesSearch && matchesCategory && matchesRegion) {
          if (total >= offset && filtered.length < limit) {
            filtered.push(b);
          }
          total++;
        }
        cursor.continue();
      } else {
        // No more items
        resolve({
          billers: filtered,
          total: total,
        });
      }
    };

    request.onerror = () => reject(request.error);
  });
}

export async function getUniqueCategoriesAndRegions(): Promise<{ categories: string[]; regions: string[] }> {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction('billers', 'readonly');
    const store = tx.objectStore('billers');
    const request = store.openCursor();

    const categoriesSet = new Set<string>();
    const regionsSet = new Set<string>();

    request.onsuccess = (event) => {
      const cursor = (event.target as IDBRequest).result as IDBCursorWithValue;
      if (cursor) {
        const b = cursor.value as Biller;
        if (b.category) categoriesSet.add(b.category);
        if (b.region) regionsSet.add(b.region);
        cursor.continue();
      } else {
        resolve({
          categories: Array.from(categoriesSet).sort(),
          regions: Array.from(regionsSet).sort(),
        });
      }
    };

    request.onerror = () => reject(request.error);
  });
}

export async function getCacheCount(): Promise<number> {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction('billers', 'readonly');
    const store = tx.objectStore('billers');
    const request = store.count();

    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

import { useAuthStore } from '../state/authStore';

export async function hydrateBillerCache(
  sourceId: string,
  onProgress: (percent: number, statusText: string) => void
): Promise<void> {
  onProgress(5, 'Initiating direct authenticated stream hydration...');
  
  const baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
  const url = `${baseUrl}/BOBCOU/BBPS/${sourceId}/billpay/billers/stream`;
  
  const { apiKey, jwtToken } = useAuthStore.getState();
  const headers: Record<string, string> = {
    'Accept': 'text/csv'
  };
  
  if (jwtToken) {
    headers['Authorization'] = `Bearer ${jwtToken}`;
  } else if (apiKey) {
    headers['X-API-Key'] = apiKey;
  }

  // 1. Fetch direct stream
  const response = await fetch(url, { headers });
  if (!response.ok) {
    const errorBody = await response.text();
    throw new Error(`Server returned ${response.status}: ${errorBody || response.statusText}`);
  }

  if (!response.body) {
    throw new Error('Readable stream not supported in response body.');
  }

  onProgress(15, 'Database connection established. Streaming data chunks...');

  const reader = response.body.getReader();
  const decoder = new TextDecoder('utf-8');
  let buffer = '';
  let linesCount = 0;
  let hasHeader = false;
  
  await clearCache();
  
  // To avoid writing to IndexedDB for every single line which causes high transactional overhead,
  // we will buffer records in batches (e.g. 250 records) and write in chunks.
  let batch: Biller[] = [];
  const batchSize = 250;
  
  // Total expected records to estimate progress (10,000 BBPS operators)
  const expectedTotal = 10000;

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    
    let lineEndIndex;
    while ((lineEndIndex = buffer.indexOf('\n')) !== -1) {
      const line = buffer.substring(0, lineEndIndex).trim();
      buffer = buffer.substring(lineEndIndex + 1);

      if (!line) continue;

      if (!hasHeader) {
        // Skip header line
        hasHeader = true;
        continue;
      }

      const parts = parseCSVLine(line);
      if (parts.length < 4) continue; // Malformed row

      const biller: Biller = {
        biller_id: parts[0],
        biller_name: parts[1],
        category: parts[2],
        region: parts[3],
        metadata: {
          state: parts[4],
          city: parts[5],
          support_email: parts[6],
          support_phone: parts[7],
          payment_modes: parts[8] ? parts[8].split(';') : [],
          min_amount: parts[9],
          max_amount: parts[10],
          active_status: parts[11],
          provider_latency_ms: parseInt(parts[12], 10) || 100,
          failure_probability: parseFloat(parts[13]) || 0.0,
          created_at: parts[14]
        }
      };

      batch.push(biller);
      linesCount++;

      if (batch.length >= batchSize) {
        await saveBillersInChunks(batch, 50);
        batch = [];
        // Update progress dynamically
        const progress = Math.min(95, Math.round(15 + (linesCount * 80) / expectedTotal));
        onProgress(progress, `Hydrating operator cache: ${linesCount} records...`);
      }
    }
  }

  // Handle final leftover buffer if any
  if (buffer.trim()) {
    const line = buffer.trim();
    if (hasHeader) {
      const parts = parseCSVLine(line);
      if (parts.length >= 4) {
        const biller: Biller = {
          biller_id: parts[0],
          biller_name: parts[1],
          category: parts[2],
          region: parts[3],
          metadata: {
            state: parts[4],
            city: parts[5],
            support_email: parts[6],
            support_phone: parts[7],
            payment_modes: parts[8] ? parts[8].split(';') : [],
            min_amount: parts[9],
            max_amount: parts[10],
            active_status: parts[11],
            provider_latency_ms: parseInt(parts[12], 10) || 100,
            failure_probability: parseFloat(parts[13]) || 0.0,
            created_at: parts[14]
          }
        };
        batch.push(biller);
        linesCount++;
      }
    }
  }

  if (batch.length > 0) {
    await saveBillersInChunks(batch, 50);
  }

  onProgress(100, `Successfully hydrated ${linesCount} records into IndexedDB cache.`);
}

function parseCSVLine(line: string): string[] {
  const result: string[] = [];
  let current = '';
  let inQuotes = false;
  for (let i = 0; i < line.length; i++) {
    const char = line[i];
    if (char === '"') {
      inQuotes = !inQuotes;
    } else if (char === ',' && !inQuotes) {
      result.push(current);
      current = '';
    } else {
      current += char;
    }
  }
  result.push(current);
  return result;
}
