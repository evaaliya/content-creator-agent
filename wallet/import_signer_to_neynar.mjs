import { ViemLocalEip712Signer } from '@farcaster/hub-nodejs';
import { mnemonicToAccount } from 'viem/accounts';
import fetch from 'node-fetch';
import dotenv from 'dotenv';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
dotenv.config({ path: path.join(__dirname, '..', '.env') });

const mnemonic = "task vague parrot warm siren tank lava grunt object manage region either";
const account = mnemonicToAccount(mnemonic);
const fid = process.env.FARCASTER_FID;
const publicKey = process.env.FARCASTER_SIGNER_PUBLIC_KEY;
const apiKey = process.env.NEYNAR_API_KEY;

async function main() {
  console.log("🔗 Importing on-chain signer to Neynar...");

  const deadline = Math.floor(Date.now() / 1000) + 86400; // 24 hours
  const eip712Signer = new ViemLocalEip712Signer(account);
  
  // Convert hex public key to bytes
  const publicKeyBytes = Buffer.from(publicKey.replace('0x', ''), 'hex');

  const signatureResult = await eip712Signer.signKeyRequest({
    requestFid: BigInt(fid),
    key: publicKeyBytes,
    deadline: BigInt(deadline),
  });

  if (signatureResult.isErr()) {
      throw new Error(`Failed to sign key request: ${signatureResult.error}`);
  }
  const signature = Buffer.from(signatureResult.value).toString('hex');

  const res = await fetch('https://api.neynar.com/v2/farcaster/signer/signed_key', {
    method: 'POST',
    headers: {
      'api_key': apiKey,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      signer_public_key: publicKey,
      signature: '0x' + signature,
      deadline: deadline,
      fid: fid
    })
  });

  const data = await res.json();
  console.log(JSON.stringify(data, null, 2));
}

main().catch(console.error);
