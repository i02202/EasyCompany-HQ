/**
 * Generate 8-direction isometric character sprites for Easy Company HQ agents.
 * Uses PixelLab API v2.
 *
 * Usage: npx tsx scripts/generate-characters.ts
 */
import 'dotenv/config';
import fs from 'fs';
import path from 'path';

const API_BASE = 'https://api.pixellab.ai/v2';
const API_KEY = process.env.PIXELLAB_API_KEY;
if (!API_KEY) throw new Error('PIXELLAB_API_KEY not set in .env');

const OUT_DIR = path.resolve('assets/characters');
fs.mkdirSync(OUT_DIR, { recursive: true });

const AGENTS = [
  { id: 'ceo',        desc: 'male CEO in dark navy suit and red tie, confident posture, short dark hair, pixel art isometric game character, transparent background' },
  { id: 'cto',        desc: 'male CTO in grey hoodie and jeans, glasses, messy hair, casual tech look, pixel art isometric game character, transparent background' },
  { id: 'cfo',        desc: 'female CFO in charcoal business suit, blonde hair in bun, professional look, pixel art isometric game character, transparent background' },
  { id: 'trader',     desc: 'male stock trader in white shirt with rolled sleeves and dark vest, loosened tie, pixel art isometric game character, transparent background' },
  { id: 'researcher', desc: 'female researcher in white lab coat over casual clothes, brown hair with ponytail, pixel art isometric game character, transparent background' },
  { id: 'hr',         desc: 'female HR manager in warm orange blouse and black pants, friendly appearance, pixel art isometric game character, transparent background' },
  { id: 'security',   desc: 'male security guard in dark uniform with cap and badge, muscular build, pixel art isometric game character, transparent background' },
  { id: 'media',      desc: 'female media specialist in colorful creative outfit, purple hair, headphones around neck, pixel art isometric game character, transparent background' },
];

async function apiPost(endpoint: string, body: Record<string, unknown>): Promise<any> {
  const res = await fetch(`${API_BASE}${endpoint}`, {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${API_KEY}`, 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  const json = await res.json();
  if (!res.ok && res.status !== 202) throw new Error(`API ${res.status}: ${JSON.stringify(json).slice(0, 300)}`);
  return json;
}

async function apiGet(endpoint: string): Promise<any> {
  const res = await fetch(`${API_BASE}${endpoint}`, {
    headers: { 'Authorization': `Bearer ${API_KEY}` },
  });
  return res.json();
}

async function pollJob(jobId: string, maxWait = 180_000): Promise<any> {
  const start = Date.now();
  while (Date.now() - start < maxWait) {
    const json = await apiGet(`/background-jobs/${jobId}`);
    if (json.status === 'completed') return json;
    if (json.status === 'failed') throw new Error(`Job failed: ${JSON.stringify(json).slice(0, 300)}`);
    process.stdout.write('.');
    await new Promise(r => setTimeout(r, 4000));
  }
  throw new Error(`Job ${jobId} timed out after ${maxWait / 1000}s`);
}

function saveImages(dir: string, result: any): number {
  // Find images in the response (structure varies by endpoint)
  const images: Array<{ base64: string }> =
    result.images || result.data?.images || result.result?.images || [];

  if (images.length === 0) {
    // Try to find base64 data elsewhere
    const flat = JSON.stringify(result);
    if (!flat.includes('base64')) return 0;
  }

  const DIRS_8 = ['S', 'SW', 'W', 'NW', 'N', 'NE', 'E', 'SE'];
  let saved = 0;
  for (let i = 0; i < images.length; i++) {
    const label = i < 8 ? DIRS_8[i] : `extra_${i}`;
    const filePath = path.join(dir, `${label}.png`);
    fs.writeFileSync(filePath, Buffer.from(images[i].base64, 'base64'));
    saved++;
  }
  return saved;
}

async function generateAgent(agent: { id: string; desc: string }): Promise<void> {
  const agentDir = path.join(OUT_DIR, agent.id);
  fs.mkdirSync(agentDir, { recursive: true });

  if (fs.existsSync(path.join(agentDir, 'S.png'))) {
    console.log(`  ⏭ ${agent.id} already exists, skipping`);
    return;
  }

  console.log(`  🎨 ${agent.id}: generating base image...`);

  // Step 1: Generate base character
  const baseResp = await apiPost('/generate-image-v2', {
    description: agent.desc,
    image_size: { width: 128, height: 128 },
  });

  let baseImage: string;
  if (baseResp.background_job_id) {
    process.stdout.write('    ⏳ waiting');
    const job = await pollJob(baseResp.background_job_id);
    console.log(' done');
    const images = job.images || job.result?.images || [];
    if (!images.length) {
      // Save full response for debugging
      fs.writeFileSync(path.join(agentDir, 'debug_base.json'), JSON.stringify(job, null, 2));
      throw new Error('No images in base job response');
    }
    baseImage = images[0].base64;
  } else if (baseResp.images?.[0]) {
    baseImage = baseResp.images[0].base64;
  } else {
    fs.writeFileSync(path.join(agentDir, 'debug_base.json'), JSON.stringify(baseResp, null, 2));
    throw new Error('Unexpected base response format');
  }

  fs.writeFileSync(path.join(agentDir, 'base.png'), Buffer.from(baseImage, 'base64'));
  console.log(`    📷 base saved`);

  // Step 2: Generate 8 rotations
  console.log(`    🔄 ${agent.id}: generating 8 rotations...`);
  const rotResp = await apiPost('/generate-8-rotations-v2', {
    description: agent.desc,
    reference_image: { type: 'base64', base64: baseImage, format: 'png' },
    image_size: { width: 128, height: 128 },
    view: 'three-quarters-top-down',
  });

  if (rotResp.background_job_id) {
    process.stdout.write('    ⏳ waiting');
    const job = await pollJob(rotResp.background_job_id);
    console.log(' done');
    const count = saveImages(agentDir, job);
    console.log(`    ✅ ${agent.id}: ${count} directions saved`);
  } else {
    const count = saveImages(agentDir, rotResp);
    console.log(`    ✅ ${agent.id}: ${count} directions saved`);
  }
}

async function main() {
  console.log('🏢 Generating Easy Company HQ agent sprites via PixelLab API\n');

  for (const agent of AGENTS) {
    try {
      await generateAgent(agent);
    } catch (err) {
      console.error(`\n  ❌ ${agent.id} failed:`, (err as Error).message);
    }
    // Small delay between agents to avoid rate limits
    await new Promise(r => setTimeout(r, 2000));
  }

  console.log(`\n✅ Done! Characters saved to ${OUT_DIR}`);
}

main();
