import { createPublicClient, http, formatEther } from 'viem';
import { base } from 'viem/chains';

export async function GET() {
  try {
    const address = process.env.PRIVY_WALLET_ADDRESS;
    if (!address) {
      return Response.json({ error: 'No wallet address configured' }, { status: 500 });
    }

    const publicClient = createPublicClient({
      chain: base,
      transport: http()
    });

    const balanceWei = await publicClient.getBalance({ address });
    const balanceEth = formatEther(balanceWei);

    return Response.json({ address, balanceEth });
  } catch (error) {
    console.error('Balance API Error:', error);
    return Response.json({ error: error.message }, { status: 500 });
  }
}
