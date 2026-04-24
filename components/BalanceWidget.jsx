'use client';

import { useEffect, useState } from 'react';

export default function BalanceWidget() {
  const [balance, setBalance] = useState(null);
  const [address, setAddress] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('/api/balance')
      .then(res => res.json())
      .then(data => {
        if (data.balanceEth) {
          setBalance(parseFloat(data.balanceEth).toFixed(4));
          setAddress(data.address.substring(0, 6) + '...' + data.address.substring(38));
        }
        setLoading(false);
      })
      .catch(err => {
        console.error(err);
        setLoading(false);
      });
  }, []);

  return (
    <div style={{
      border: '1px solid var(--neon-blue)',
      padding: '15px 20px',
      background: 'var(--panel-bg)',
      boxShadow: '0 0 15px rgba(0, 243, 255, 0.2)',
      borderRadius: '4px',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'flex-end',
      minWidth: '200px'
    }}>
      <div style={{ fontSize: '0.8rem', color: 'var(--neon-blue)', marginBottom: '5px' }}>
        AGENT WALLET
      </div>
      {loading ? (
        <div style={{ color: '#fff', fontSize: '1.2rem' }}>Loading...</div>
      ) : (
        <>
          <div style={{ color: '#fff', fontSize: '1.4rem', fontWeight: 'bold' }}>
            {balance} ETH
          </div>
          <div style={{ fontSize: '0.7rem', color: '#888', marginTop: '5px' }}>
            {address}
          </div>
        </>
      )}
    </div>
  );
}
