import { createClient } from '@supabase/supabase-js';

export async function GET() {
  try {
    const url = process.env.SUPABASE_URL;
    const key = process.env.SUPABASE_KEY;

    if (!url || !key) {
      return Response.json({ error: 'Supabase credentials missing' }, { status: 500 });
    }

    const supabase = createClient(url, key);
    
    // Fetch latest assets, ordered by timestamp
    const { data, error } = await supabase
      .from('agent_assets')
      .select('*')
      .order('timestamp', { ascending: false })
      .limit(20);

    if (error) {
      throw error;
    }

    return Response.json({ assets: data });
  } catch (error) {
    console.error('Assets API Error:', error);
    return Response.json({ error: error.message }, { status: 500 });
  }
}
