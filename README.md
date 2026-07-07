# TICONDEROGA SYSTEM HOLDINGs
## ticonderogasystem.xyz — Deployment Package

### Deploy to Vercel
1. Copy all files in this folder into your GitHub repo (overthaught-lgtm/Ticonderoga-SYS)
2. Push to main branch
3. Vercel auto-deploys
4. Point ticonderoga.online DNS to Vercel in Cloudflare

### DNS Setup (Cloudflare)
- Type: CNAME
- Name: @
- Target: cname.vercel-dns.com
- Proxy: OFF (DNS only)

### File Map
- index.html        → ticonderogasystem.xyz/
- mint.html         → ticonderogasystem.xyz/mint
- pipeline.html     → ticonderogasystem.xyz/pipeline
- systems.html      → ticonderogasystem.xyz/systems

### Octal Node Map
[0] INDYBLOC CORE
[1] GitHub source
[2] Vercel deploy
[3] Cloudflare DNS
[4] ticonderogasystem.xyz/
[5] ticonderogasystems.xyz
[6] Mint/NFT node
[7] CRM/JSWB
[8th open] Jan Jupiter / Owmosis
