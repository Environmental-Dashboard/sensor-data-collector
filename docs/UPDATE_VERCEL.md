# How to Update Vercel with Tunnel URL

The tunnel is working, but Vercel needs to be updated with the tunnel URL.

## Current Tunnel URL

Check `backend\tunnel_url.txt` for the current tunnel URL.

## Method 1: Via Vercel Dashboard (Easiest)

1. Go to https://vercel.com/dashboard
2. Select your project (frontend)
3. Go to **Settings** → **Environment Variables**
4. Find or add: `VITE_API_URL`
5. Set the value to the tunnel URL from `backend\tunnel_url.txt`
   - Example: `https://proudly-packets-emerging-investments.trycloudflare.com`
6. Click **Save**
7. Go to **Deployments** tab
8. Click the **⋯** (three dots) on the latest deployment
9. Click **Redeploy**

## Method 2: Via Vercel CLI

```powershell
cd frontend
npx vercel env rm VITE_API_URL production -y
echo "https://install-vote-unfortunately-famous.trycloudflare.com" | npx vercel env add VITE_API_URL production
npx vercel --prod
```

Replace `YOUR-TUNNEL-URL` with the actual URL from `backend\tunnel_url.txt`.

## Verify Connection

After updating:

1. Wait 1-2 minutes for deployment
2. Visit https://ed-sensor-dashboard.vercel.app
3. Check if backend connection status shows "Connected"

## Why Manual Update?

The scheduled task runs as SYSTEM user, which doesn't have npm/node properly configured. The automatic update fails, so manual update is required.

**Note:** The tunnel URL changes each time the tunnel restarts. You'll need to update Vercel whenever the tunnel URL changes.
