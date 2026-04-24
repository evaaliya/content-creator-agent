-- Enable the pgvector extension
create extension if not exists vector;

-- Create the agent_memory table for semantic search
create table agent_memory (
  id uuid primary key default gen_random_uuid(),
  created_at timestamp with time zone default timezone('utc'::text, now()) not null,
  memory_type text not null, -- e.g., 'cast', 'user_relationship', 'topic_vibe'
  content text not null,     -- The raw text content
  embedding vector(1536),    -- Assuming OpenAI embeddings (1536 dims)
  metadata jsonb default '{}'::jsonb -- Additional context (FID, cast hash, etc)
);

-- Index for faster semantic similarity search
-- CREATE INDEX on agent_memory USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Ledger for enforcing strict local financial constraints
create table tip_ledger (
  id uuid primary key default gen_random_uuid(),
  created_at timestamp with time zone default timezone('utc'::text, now()) not null,
  recipient_fid text not null,
  amount numeric not null,
  token text not null,
  tx_hash text
);

-- Main memory 🧠
create table memories (
  id uuid primary key default gen_random_uuid(),
  type text, 
  content text, 
  embedding vector(1024), 
  created_at timestamp default now(),
  metadata jsonb 
); 

--SQL in Supabase
create function match_memories (
  query_embedding vector(1024),
  match_type text,
  match_count int
)
returns table (
  id uuid,
  content text,
  similarity float
) 
language sql
as $$
  select 
      id, content,
      1 - (query_embedding <=> embedding) as similarity
  from memories 
  where type = match_type
  order by embedding <-> query_embedding
  limit match_count;
$$; 

-- Daily agent state limits
CREATE TABLE IF NOT EXISTS agent_state (
    key VARCHAR(255) PRIMARY KEY,
    value JSONB NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Agent Assets (DeSci Curation, NFTs, Tokens)
CREATE TABLE IF NOT EXISTS agent_assets (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    article_title TEXT,
    tx_hash VARCHAR(255),
    nft_url TEXT,
    insight_text TEXT,
    asset_type VARCHAR(50)
);
