// change_fname.mjs — Register fname "matricula" in Farcaster name registry
import { mnemonicToAccount } from 'viem/accounts';
import * as dotenv from 'dotenv';
dotenv.config();

const MNEMONIC = process.env.AGENT_MNEMONIC;
const FID = 3319768;
const NEW_FNAME = 'matricula';

const account = mnemonicToAccount(MNEMONIC);
const timestamp = Math.floor(Date.now() / 1000);

// EIP-712 signature for fname transfer
const domain = {
  name: 'Farcaster name verification',
  version: '1',
  chainId: 1,
  verifyingContract: '0xe3Be01D99bAa8dB9905b33a3cA391238234B79D1',
};

const types = {
  UserNameProof: [
    { name: 'name', type: 'string' },
    { name: 'timestamp', type: 'uint256' },
    { name: 'owner', type: 'address' },
  ],
};

const message = {
  name: NEW_FNAME,
  timestamp: BigInt(timestamp),
  owner: account.address,
};

console.log(`\n🏷️  Registering fname "${NEW_FNAME}" for FID ${FID}...`);
console.log(`   Owner: ${account.address}`);
console.log(`   Timestamp: ${timestamp}`);

const signature = await account.signTypedData({
  domain,
  types,
  primaryType: 'UserNameProof',
  message,
});

console.log(`   Signature: ${signature.slice(0, 22)}...`);

// Submit to fname registry
const res = await fetch('https://fnames.farcaster.xyz/transfers', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    name: NEW_FNAME,
    from: 0,
    fid: FID,
    owner: account.address,
    timestamp,
    signature,
  }),
});

const data = await res.json();
console.log(`   Status: ${res.status}`);
console.log('   Response:', JSON.stringify(data, null, 2));

if (res.ok) {
  console.log(`\n✅ fname "${NEW_FNAME}" registered! Now updating profile...`);
  
  // Now update the profile with the new fname
  const updateRes = await fetch('https://api.neynar.com/v2/farcaster/user', {
    method: 'PATCH',
    headers: {
      'api_key': process.env.NEYNAR_API_KEY,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      signer_uuid: '2b1131c9-3aff-4863-ba67-621372425123',
      username: NEW_FNAME,
    }),
  });
  const updateData = await updateRes.json();
  console.log('   Profile update:', JSON.stringify(updateData));
}
