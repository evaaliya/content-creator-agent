import { PrivyClient } from '@privy-io/server-auth';
const client = new PrivyClient('a', 'b');
console.log(client.walletApi);
