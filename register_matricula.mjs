// register_matricula.mjs — Register a NEW account with fname "matricula"
import { ID_REGISTRY_ADDRESS, ViemLocalEip712Signer, idRegistryABI } from '@farcaster/hub-nodejs';
import { bytesToHex, createPublicClient, http } from 'viem';
import { generateMnemonic, english, mnemonicToAccount } from 'viem/accounts';
import { optimism } from 'viem/chains';
import * as dotenv from 'dotenv';
dotenv.config();

const NEYNAR_API_KEY = process.env.NEYNAR_API_KEY;
const NEYNAR_WALLET_ID = 'zy6lpyxw8w6eaqgrawkkv0i4';
const AGENT_USERNAME = 'matricula';

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

// Step 1: Get fresh FID
console.log('\n🔍 Getting fresh FID...');
const fidRes = await fetch('https://api.neynar.com/v2/farcaster/user/fid', { headers });
const fidData = await fidRes.json();
if (!fidRes.ok) { console.error('❌', fidData); process.exit(1); }
const fid = fidData.fid;
console.log(`   ✅ FID: ${fid}`);

// Step 2: Generate wallet
console.log('\n🔑 Generating wallet...');
const mnemonic = generateMnemonic(english);
const account = mnemonicToAccount(mnemonic);
console.log(`   Address: ${account.address}`);
console.log(`   ⚠️  MNEMONIC: ${mnemonic}`);

// Step 3: Sign
console.log('\n✍️  Signing...');
const deadline = BigInt(Math.floor(Date.now() / 1000) + 3600);
const signer = new ViemLocalEip712Signer(account);
const nonce = await publicClient.readContract({
  address: ID_REGISTRY_ADDRESS,
  abi: idRegistryABI,
  functionName: 'nonces',
  args: [account.address],
});
const signature = await signer.signTransfer({
  fid: BigInt(fid),
  to: account.address,
  nonce,
  deadline,
});
if (signature.isErr()) { console.error('❌ Sign failed'); process.exit(1); }
const sigHex = bytesToHex(signature.value);
console.log(`   ✅ Signed`);

// Step 4: Register with fname "matricula"
console.log(`\n🚀 Registering @${AGENT_USERNAME}...`);
const regRes = await fetch('https://api.neynar.com/v2/farcaster/user', {
  method: 'POST',
  headers,
  body: JSON.stringify({
    fid,
    fname: AGENT_USERNAME,
    signature: sigHex,
    requested_user_custody_address: account.address,
    deadline: Number(deadline),
    metadata: {
      bio: 'enrolled in everything. committed to nothing.',
      display_name: 'Matriculate',
      username: AGENT_USERNAME,
      pfp_url: 'https://files.catbox.moe/d3dw2n.jpg'
    }
  }),
});
const regData = await regRes.json();
console.log(`   Status: ${regRes.status}`);
console.log(JSON.stringify(regData, null, 2));

if (regData.success) {
  const s = regData.signer || {};
  console.log('\n' + '='.repeat(50));
  console.log('✅ @matricula created! Update .env:');
  console.log('='.repeat(50));
  console.log(`FARCASTER_FID=${regData.user?.fid || fid}`);
  console.log(`FARCASTER_SIGNER_UUID=${s.signer_uuid}`);
  console.log(`AGENT_MNEMONIC=${mnemonic}`);
  console.log(`AGENT_CUSTODY_ADDRESS=${account.address}`);
}
