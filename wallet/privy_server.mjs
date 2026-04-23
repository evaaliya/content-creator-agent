import { PrivyClient } from '@privy-io/node';
import { createViemAccount } from '@privy-io/node/viem';
import { createPublicClient, http } from 'viem';
import { arbitrum } from 'viem/chains';
import dotenv from 'dotenv';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
dotenv.config({ path: path.join(__dirname, '..', '.env') });

const privy = new PrivyClient({
  appId: process.env.PRIVY_APP_ID,
  appSecret: process.env.PRIVY_APP_SECRET,
});

const walletId = process.env.PRIVY_WALLET_ID;
const address = process.env.PRIVY_WALLET_ADDRESS;
const authorizationPrivateKey = process.env.PRIVY_AUTHORIZATION_PRIVATE_KEY;

if (!walletId || !address || !authorizationPrivateKey) {
  console.error(JSON.stringify({
    success: false,
    error: "Missing PRIVY_WALLET_ID, PRIVY_WALLET_ADDRESS, or PRIVY_AUTHORIZATION_PRIVATE_KEY in .env"
  }));
  process.exit(1);
}

const account = createViemAccount(privy, {
  walletId,
  address,
  authorizationContext: {
    authorizationPrivateKey,
  }
});

const arbitrumClient = createPublicClient({
  chain: arbitrum,
  transport: http()
});

const command = process.argv[2];
const payloadStr = process.argv[3];

async function main() {
  try {
    const payload = JSON.parse(payloadStr || '{}');

    if (command === 'personal_sign') {
      const signature = await account.signMessage({
        message: payload.message
      });
      console.log(JSON.stringify({ success: true, result: signature }));
    } 
    else if (command === 'eth_signTypedData_v4') {
      const td = payload.typed_data;
      const signature = await account.signTypedData({
        domain: td.domain,
        types: td.types,
        primaryType: td.primaryType || td.primary_type,
        message: td.message
      });
      console.log(JSON.stringify({ success: true, result: signature }));
    }
    else if (command === 'eth_sendTransaction') {
      const tx = payload.transaction;
      const request = await arbitrumClient.prepareTransactionRequest({
        account,
        to: tx.to,
        value: BigInt(tx.value)
      });
      const signature = await account.signTransaction(request);
      const txHash = await arbitrumClient.sendRawTransaction({
        serializedTransaction: signature
      });
      console.log(JSON.stringify({ success: true, result: txHash }));
    }
    else {
      console.error(JSON.stringify({ success: false, error: "Unknown command" }));
      process.exit(1);
    }
  } catch (err) {
    console.error(JSON.stringify({ success: false, error: err.message, stack: err.stack }));
    process.exit(1);
  }
}

main();
