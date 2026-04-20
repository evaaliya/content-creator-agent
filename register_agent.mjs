// register_agent.mjs — One-time script to create a new Farcaster account for the agent
// Based on official Neynar docs: https://docs.neynar.com/docs/how-to-create-a-new-farcaster-account-with-neynar

import { ID_REGISTRY_ADDRESS, ViemLocalEip712Signer, idRegistryABI } from '@farcaster/hub-nodejs';
import { bytesToHex, createPublicClient, http } from 'viem';
import { generateMnemonic, english, mnemonicToAccount } from 'viem/accounts';
import { optimism } from 'viem/chains';
import * as dotenv from 'dotenv';
dotenv.config();

const NEYNAR_API_KEY = process.env.NEYNAR_API_KEY;
const NEYNAR_WALLET_ID = 'zy6lpyxw8w6eaqgrawkkv0i4';
const AGENT_USERNAME = 'eva8agent'; // change if taken

const headers = {
  'api_key': NEYNAR_API_KEY,
  'x-api-key': NEYNAR_API_KEY,
  'x-wallet-id': NEYNAR_WALLET_ID,
  'Content-Type': 'application/json'
};

const publicClient = createPublicClient({
  chain: optimism,
  transport: http(),
});

// ── Step 1: Get fresh FID ──────────────────────────────────────
async function getFreshFid() {
  console.log('\n🔍 Step 1: Getting fresh FID from Neynar...');
  const res = await fetch('https://api.neynar.com/v2/farcaster/user/fid', { headers });
  const data = await res.json();
  if (!res.ok) {
    console.error('   ❌ Error:', data);
    process.exit(1);
  }
  console.log(`   ✅ Reserved FID: ${data.fid}`);
  return data.fid;
}

// ── Step 2: Generate new agent wallet ─────────────────────────
function generateAgentWallet() {
  console.log('\n🔑 Step 2: Generating new agent wallet...');
  const mnemonic = generateMnemonic(english);
  const account = mnemonicToAccount(mnemonic);
  console.log(`   ✅ Address: ${account.address}`);
  console.log(`   ⚠️  SAVE THIS MNEMONIC (12 words): ${mnemonic}`);
  return { mnemonic, account };
}

// ── Step 3: Sign Transfer message ─────────────────────────────
async function signRegistration(fid, account) {
  console.log('\n✍️  Step 3: Signing registration (Transfer)...');
  const deadline = BigInt(Math.floor(Date.now() / 1000) + 3600); // 1 hour

  const signer = new ViemLocalEip712Signer(account);

  const nonce = await publicClient.readContract({
    address: ID_REGISTRY_ADDRESS,
    abi: idRegistryABI,
    functionName: 'nonces',
    args: [account.address],
  });
  console.log(`   Nonce from chain: ${nonce}`);

  const signature = await signer.signTransfer({
    fid: BigInt(fid),
    to: account.address,
    nonce,
    deadline,
  });

  if (signature.isErr()) {
    console.error('   ❌ Signing failed:', signature.error);
    process.exit(1);
  }

  const sigHex = bytesToHex(signature.value);
  console.log(`   ✅ Signature: ${sigHex.slice(0, 22)}...`);
  return { sigHex, deadline: Number(deadline) };
}

// ── Step 4: Register account ───────────────────────────────────
async function registerAccount(fid, sigHex, custodyAddress, deadline) {
  console.log(`\n🚀 Step 4: Registering @${AGENT_USERNAME}...`);
  const body = {
    fid,
    fname: AGENT_USERNAME,
    signature: sigHex,
    requested_user_custody_address: custodyAddress,
    deadline,
  };

  const res = await fetch('https://api.neynar.com/v2/farcaster/user', {
    method: 'POST',
    headers,
    body: JSON.stringify(body),
  });

  const data = await res.json();
  console.log(`   Status: ${res.status}`);
  console.log('   Response:', JSON.stringify(data, null, 2));
  return data;
}

// ── MAIN ───────────────────────────────────────────────────────
(async () => {
  console.log('='.repeat(50));
  console.log('🤖 Creating new Farcaster agent account');
  console.log('='.repeat(50));

  const fid = await getFreshFid();
  const { mnemonic, account } = generateAgentWallet();
  const { sigHex, deadline } = await signRegistration(fid, account);
  const result = await registerAccount(fid, sigHex, account.address, deadline);

  if (result.success) {
    const signer = result.signer || {};
    const user = result.user || {};
    console.log('\n' + '='.repeat(50));
    console.log('✅ SUCCESS! Add these to .env:');
    console.log('='.repeat(50));
    console.log(`AGENT_FID=${user.fid || fid}`);
    console.log(`AGENT_SIGNER_UUID=${signer.signer_uuid}`);
    console.log(`AGENT_MNEMONIC=${mnemonic}`);
    console.log(`AGENT_CUSTODY_ADDRESS=${account.address}`);
  }
})();
