import fetch from 'node-fetch';
import dotenv from 'dotenv';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
dotenv.config({ path: path.join(__dirname, '..', '.env') });

const appId = process.env.PRIVY_APP_ID;
const appSecret = process.env.PRIVY_APP_SECRET;

async function main() {
  const auth = Buffer.from(`${appId}:${appSecret}`).toString('base64');
  const res = await fetch('https://api.privy.io/v1/wallets?chain_type=solana', {
    headers: {
      'Authorization': `Basic ${auth}`,
      'privy-app-id': appId
    }
  });
  const data = await res.json();
  console.log(JSON.stringify(data, null, 2));
}

main();
