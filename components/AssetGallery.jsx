'use client';

import { useEffect, useState } from 'react';

export default function AssetGallery() {
  const [assets, setAssets] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('/api/assets')
      .then(res => res.json())
      .then(data => {
        if (data.assets) {
          setAssets(data.assets);
        }
        setLoading(false);
      })
      .catch(err => {
        console.error(err);
        setLoading(false);
      });
  }, []);

  if (loading) {
    return <div style={{ color: 'var(--neon-blue)' }}>[ FETCHING ASSETS... ]</div>;
  }

  if (assets.length === 0) {
    return (
      <div style={{ 
        border: '1px dashed var(--neon-pink)', 
        padding: '40px', 
        textAlign: 'center',
        color: 'var(--neon-pink)'
      }}>
        [ NO DESCI ASSETS FOUND IN DATABASE ]
      </div>
    );
  }

  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))',
      gap: '25px',
      marginTop: '20px'
    }}>
      {assets.map(asset => (
        <div key={asset.id} style={{
          background: 'var(--panel-bg)',
          border: '1px solid var(--grid-line)',
          borderTop: '2px solid var(--neon-blue)',
          padding: '20px',
          display: 'flex',
          flexDirection: 'column',
          position: 'relative',
          transition: 'all 0.3s ease',
          boxShadow: '0 5px 15px rgba(0,0,0,0.5)'
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.boxShadow = '0 0 20px rgba(0, 243, 255, 0.3)';
          e.currentTarget.style.borderColor = 'var(--neon-blue)';
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.boxShadow = '0 5px 15px rgba(0,0,0,0.5)';
          e.currentTarget.style.borderColor = 'var(--grid-line)';
          e.currentTarget.style.borderTopColor = 'var(--neon-blue)';
        }}>
          {/* Asset Type Badge */}
          <div style={{
            position: 'absolute',
            top: '-10px',
            right: '15px',
            background: 'var(--dark-bg)',
            color: 'var(--neon-pink)',
            border: '1px solid var(--neon-pink)',
            padding: '2px 8px',
            fontSize: '0.7rem',
            textTransform: 'uppercase'
          }}>
            {asset.asset_type || 'Asset'}
          </div>

          {/* Title */}
          <h3 style={{ 
            color: '#fff', 
            fontSize: '1.1rem', 
            marginTop: '10px',
            marginBottom: '15px',
            lineHeight: '1.4'
          }}>
            {asset.article_title}
          </h3>

          {/* AI Insight */}
          <div style={{
            background: 'rgba(0,0,0,0.5)',
            borderLeft: '2px solid var(--neon-pink)',
            padding: '10px 15px',
            marginBottom: '20px',
            flexGrow: 1
          }}>
            <p style={{ color: '#aaa', fontSize: '0.85rem', margin: '0 0 5px 0' }}>// AI INSIGHT</p>
            <p style={{ color: '#eee', fontSize: '0.9rem', margin: 0, lineHeight: '1.5' }}>
              {asset.insight_text}
            </p>
          </div>

          {/* Links Footer */}
          <div style={{ 
            display: 'flex', 
            justifyContent: 'space-between',
            borderTop: '1px solid var(--grid-line)',
            paddingTop: '15px',
            fontSize: '0.8rem'
          }}>
            <a 
              href={`https://basescan.org/tx/${asset.tx_hash}`} 
              target="_blank" 
              rel="noreferrer"
              style={{ color: 'var(--neon-blue)', textDecoration: 'none' }}
            >
              [ BASESCAN ]
            </a>
            
            {asset.nft_url && (
              <a 
                href={asset.nft_url} 
                target="_blank" 
                rel="noreferrer"
                style={{ color: 'var(--neon-pink)', textDecoration: 'none' }}
              >
                [ VIEW ASSET ]
              </a>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
