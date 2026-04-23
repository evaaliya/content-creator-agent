import { 
    KEY_GATEWAY_ADDRESS, 
    SIGNED_KEY_REQUEST_VALIDATOR_ADDRESS,
    keyGatewayABI,
    signedKeyRequestValidatorABI,
    ViemLocalEip712Signer
} from '@farcaster/hub-nodejs';
import { createPublicClient, createWalletClient, http, hexToBytes, bytesToHex } from 'viem';
import { mnemonicToAccount } from 'viem/accounts';
import { optimism } from 'viem/chains';
import * as ed25519 from '@noble/ed25519';
import dotenv from 'dotenv';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
dotenv.config({ path: path.join(__dirname, '..', '.env') });

// Custody wallet from mnemonic
const mnemonic = "task vague parrot warm siren tank lava grunt object manage region either";
const account = mnemonicToAccount(mnemonic);
const fid = BigInt(process.env.FARCASTER_FID);

const publicClient = createPublicClient({
  chain: optimism,
  transport: http(),
});

const walletClient = createWalletClient({
  account,
  chain: optimism,
  transport: http(),
});

async function main() {
  console.log(`🚀 Registering Self-Custody Signer for FID ${fid}...`);
  console.log(`👛 Using Custody Address: ${account.address}`);

  // 1. Generate a new Ed25519 keypair
  const privateKeyBytes = ed25519.utils.randomPrivateKey();
  const publicKeyBytes = await ed25519.getPublicKey(privateKeyBytes);
  
  const signerPrivateKey = bytesToHex(privateKeyBytes);
  const signerPublicKey = bytesToHex(publicKeyBytes);

  console.log(`🔑 New Signer Public Key: ${signerPublicKey}`);

  // 2. Prepare the SignedKeyRequest
  const deadline = BigInt(Math.floor(Date.now() / 1000) + 3600); // 1 hour from now
  
  const eip712Signer = new ViemLocalEip712Signer(account);
  
  // Metadata for the KeyGateway.add call
  // We need to use the validator contract to encode metadata correctly
  const metadataResult = await eip712Signer.getSignedKeyRequestMetadata({
    requestFid: fid,
    key: publicKeyBytes,
    deadline,
  });

  if (metadataResult.isErr()) {
      throw new Error(`Failed to generate metadata: ${metadataResult.error}`);
  }
  const metadata = bytesToHex(metadataResult.value);

  // 3. Call KeyGateway.add
  console.log("📨 Sending transaction to Optimism...");
  const { request } = await publicClient.simulateContract({
    account,
    address: KEY_GATEWAY_ADDRESS,
    abi: keyGatewayABI,
    functionName: 'add',
    args: [
        1, // KeyType.Ed25519
        signerPublicKey,
        1, // MetadataType.SignedKeyRequest
        metadata
    ],
  });

  const hash = await walletClient.writeContract(request);
  console.log(`✅ Transaction sent! Hash: ${hash}`);
  console.log("⏳ Waiting for confirmation...");
  
  await publicClient.waitForTransactionReceipt({ hash });
  console.log("🎉 Signer registered on-chain!");

  console.log("\n--- SAVE THIS TO YOUR .env ---");
  console.log(`FARCASTER_SIGNER_PRIVATE_KEY=${signerPrivateKey}`);
  console.log(`FARCASTER_SIGNER_PUBLIC_KEY=${signerPublicKey}`);
  console.log("------------------------------");
}

main().catch(err => {
    console.error("❌ Error:", err);
    process.exit(1);
});
