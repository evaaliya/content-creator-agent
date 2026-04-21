/**
 * verify_wallet.mjs — Link the agent's custody wallet as a verified address on Farcaster.
 * 
 * This signs an EIP-712 "VerificationClaim" with the custody wallet's private key
 * and submits it to Neynar to verify the address on the @matricula profile.
 * 
 * Run once: node verify_wallet.mjs
 */
import { createPublicClient, createWalletClient, http } from 'viem';
import { mnemonicToAccount } from 'viem/accounts';
import { optimism } from 'viem/chains';
import * as dotenv from 'dotenv';
dotenv.config();

const NEYNAR_API_KEY = process.env.NEYNAR_API_KEY;
const SIGNER_UUID = process.env.FARCASTER_SIGNER_UUID;
const FID = parseInt(process.env.FARCASTER_FID);
const MNEMONIC = process.env.AGENT_MNEMONIC;

// The address we want to verify (custody wallet derived from mnemonic)
const account = mnemonicToAccount(MNEMONIC);
const ADDRESS = account.address;

console.log(`🔑 Verifying address: ${ADDRESS}`);
console.log(`📋 FID: ${FID}`);
console.log(`🔏 Signer: ${SIGNER_UUID}`);

// Step 1: Get latest Optimism block hash (needed for EIP-712 claim)
const publicClient = createPublicClient({
  chain: optimism,
  transport: http(),
});

const block = await publicClient.getBlock();
const BLOCK_HASH = block.hash;
console.log(`📦 Block hash: ${BLOCK_HASH}`);

// Step 2: Build EIP-712 VerificationClaim
// Farcaster verification claim typed data (protocol v2)
const VERIFICATION_CLAIM = {
  domain: {
    name: "Farcaster Verify Ethereum Address",
    version: "2.0.0",
    salt: '0x' + Buffer.from('farcaster-verify-ethereum-address').toString('hex').padEnd(64, '0'),
  },
  types: {
    VerificationClaim: [
      { name: "fid", type: "uint256" },
      { name: "address", type: "address" },
      { name: "blockHash", type: "bytes32" },
      { name: "network", type: "uint8" },
    ],
  },
  primaryType: "VerificationClaim",
  message: {
    fid: BigInt(FID),
    address: ADDRESS,
    blockHash: BLOCK_HASH,
    network: 1, // FARCASTER_NETWORK_MAINNET
  },
};

// Step 3: Sign with custody wallet
console.log('✍️ Signing EIP-712 claim...');
const signature = await account.signTypedData(VERIFICATION_CLAIM);
console.log(`📝 Signature: ${signature.slice(0, 20)}...`);

// Step 4: Submit to Neynar
console.log('📤 Submitting verification to Neynar...');
const response = await fetch('https://api.neynar.com/v2/farcaster/user/verification', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'x-api-key': NEYNAR_API_KEY,
    'api_key': NEYNAR_API_KEY,
  },
  body: JSON.stringify({
    signer_uuid: SIGNER_UUID,
    address: ADDRESS,
    block_hash: BLOCK_HASH,
    eth_signature: signature,
    verification_type: 1,
    chain_id: 10, // Optimism (where Farcaster identity lives)
  }),
});

const result = await response.json();
if (response.ok) {
  console.log('✅ Wallet verified on Farcaster profile!');
  console.log(JSON.stringify(result, null, 2));
} else {
  console.log(`❌ Failed: ${response.status}`);
  console.log(JSON.stringify(result, null, 2));
}
