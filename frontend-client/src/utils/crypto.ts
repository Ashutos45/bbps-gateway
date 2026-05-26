/**
 * Native cryptographic and JSON canonicalization utilities for the BBPS NextGen Ecosystem.
 * Uses the Web Cryptography API (window.crypto.subtle) to calculate HMAC-SHA256 signatures.
 */

export function canonicalize(obj: any): string {
  if (obj === null || obj === undefined) return 'null';
  
  if (typeof obj !== 'object') {
    // Return primitive representation
    if (typeof obj === 'string') {
      return `"${obj}"`;
    }
    return String(obj);
  }
  
  if (Array.isArray(obj)) {
    return '[' + obj.map(item => canonicalize(item)).join(',') + ']';
  }
  
  const sortedKeys = Object.keys(obj).sort();
  const parts = sortedKeys.map(key => {
    return `"${key}":${canonicalize(obj[key])}`;
  });
  
  return '{' + parts.join(',') + '}';
}

export async function calculateHmacSha256(message: string, secret: string): Promise<string> {
  const encoder = new TextEncoder();
  const keyData = encoder.encode(secret);
  const messageData = encoder.encode(message);

  const cryptoKey = await window.crypto.subtle.importKey(
    'raw',
    keyData,
    { name: 'HMAC', hash: 'SHA-256' },
    false,
    ['sign']
  );

  const signatureBuffer = await window.crypto.subtle.sign(
    'HMAC',
    cryptoKey,
    messageData
  );

  const signatureArray = Array.from(new Uint8Array(signatureBuffer));
  const hexSignature = signatureArray
    .map(b => b.toString(16).padStart(2, '0'))
    .join('');

  return hexSignature;
}

export function generateNonce(): string {
  // Generate a random UUID-like string
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === 'x' ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}
