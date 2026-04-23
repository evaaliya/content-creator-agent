import { PrivyClient } from '@privy-io/node';
import dotenv from 'dotenv';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
dotenv.config({ path: path.join(__dirname, '..', '.env') });

const privy = new PrivyClient({
  appId: process.env.PRIVY_APP_ID,
  appSecret: process.env.PRIVY_APP_SECRET,
});

async function main() {
  try {
    const wallets = await privy.walletsService.getWallets({ chainType: 'solana' });
    // We expect only one Solana wallet for this app account
    if (wallets.data.length > 0) {
        console.log(JSON.stringify({ success: true, address: wallets.data[0].address }));
    } else {
        // If not exists, create one
        const wallet = await privy.walletsService.create({ chainType: 'solana' });
        console.log(JSON.stringify({ success: true, address: wallet.address, created: true }));
    }
  } catch (err) {
    console.error(JSON.stringify({ success: false, error: err.message }));
    process.exit(1);
  }
}

main();
