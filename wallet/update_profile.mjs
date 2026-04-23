import fetch from 'node-fetch';
import dotenv from 'dotenv';
dotenv.config();

const apiKey = process.env.NEYNAR_API_KEY;
const signerUuid = process.env.FARCASTER_SIGNER_UUID; // Use this to update profile if needed

async function updateProfile() {
    console.log("📝 Updating agent profile with website URL...");
    
    // Farcaster User Data: Type 3 is URL, Type 1 is BIO
    // We'll add a URL to the bio and the URL field if possible
    
    const res = await fetch('https://api.neynar.com/v2/farcaster/user', {
        method: 'PATCH',
        headers: {
            'api_key': apiKey,
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            signer_uuid: signerUuid,
            url: "https://github.com/evaaliya/matricula",
            bio: "Autonomous AI Agent built with @farcaster-agent. Exploring the intersection of AI and Web3. 🤖⚡"
        })
    });

    const data = await res.json();
    console.log(JSON.stringify(data, null, 2));
}

updateProfile();
