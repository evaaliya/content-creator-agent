#!/usr/bin/env node
/**
 * LI.FI Balance Checker — Node.js wrapper called from Python.
 * 
 * Usage: node wallet/lifi_check.mjs <wallet_address>
 * Output: JSON with balances per chain
 */
import { createConfig, getWalletBalances } from '@lifi/sdk';
import { formatEther, formatUnits } from 'ethers';

const ZERO_ADDRESS = '0x0000000000000000000000000000000000000000';

const CHAIN_BY_ID = {
  1:     { key: 'ethereum',  name: 'Ethereum' },
  10:    { key: 'optimism',  name: 'Optimism' },
  8453:  { key: 'base',      name: 'Base' },
  42161: { key: 'arbitrum',  name: 'Arbitrum' },
  137:   { key: 'polygon',   name: 'Polygon' },
};

const USDC_BY_CHAIN = {
  1:     '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48',
  10:    '0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85',
  8453:  '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913',
  42161: '0xaf88d065e77c8cC2239327C5EDb3A432268e5831',
  137:   '0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359',
};

function tokenAmount(tokens, predicate) {
  const t = (tokens || []).find(predicate);
  if (!t || !t.amount) return 0n;
  try { return BigInt(t.amount); } catch { return 0n; }
}

async function main() {
  const address = process.argv[2] || process.env.PRIVY_WALLET_ADDRESS;
  if (!address) {
    console.error(JSON.stringify({ error: 'No wallet address provided' }));
    process.exit(1);
  }

  createConfig({
    integrator: 'matricula-agent',
    apiKey: process.env.LIFI_API_KEY,
  });

  try {
    const rawBalances = await getWalletBalances(address);
    const result = {};

    for (const [chainIdStr, cfg] of Object.entries(CHAIN_BY_ID)) {
      const chainId = Number(chainIdStr);
      const tokens = rawBalances[chainId] || [];

      const native = tokenAmount(tokens, t =>
        String(t.address || '').toLowerCase() === ZERO_ADDRESS
      );
      const usdcAddr = (USDC_BY_CHAIN[chainId] || '').toLowerCase();
      const usdc = tokenAmount(tokens, t =>
        String(t.address || '').toLowerCase() === usdcAddr
      );

      // Collect other tokens
      const otherTokens = [];
      for (const t of tokens) {
        const addr = String(t.address || '').toLowerCase();
        if (addr === ZERO_ADDRESS || addr === usdcAddr) continue;
        const amt = tokenAmount([t], () => true);
        if (amt > 0n) {
          otherTokens.push({
            symbol: t.symbol || 'UNKNOWN',
            amount: formatUnits(amt, t.decimals || 18),
            address: t.address,
          });
        }
      }

      result[cfg.key] = {
        chain: cfg.name,
        chainId,
        eth: formatEther(native),
        usdc: formatUnits(usdc, 6),
        otherTokens,
      };
    }

    console.log(JSON.stringify(result, null, 2));
  } catch (e) {
    console.error(JSON.stringify({ error: e.message }));
    process.exit(1);
  }
}

main();
