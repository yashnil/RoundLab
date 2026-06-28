# Dissio Deployment Guide

This guide walks through deploying Dissio for production use.

---

## Quick Deployment Checklist

For a first-time staging deployment:

1. **Supabase Setup**
   - [ ] Create Supabase project
   - [ ] Apply all 5 migrations in order (see [Supabase Setup](#supabase-setup))
   - [ ] Create `audio` storage bucket
   - [ ] Configure auth providers and redirect URLs

2. **Backend Deployment (Render/Railway)**
   - [ ] Deploy from GitHub repository
   - [ ] Set root directory to `backend`
   - [ ] Set start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - [ ] Add environment variables (see [backend/.env.example](../backend/.env.example))
   - [ ] Verify health endpoint: `https://your-backend-url/health`

3. **Frontend Deployment (Vercel)**
   - [ ] Deploy from GitHub repository
   - [ ] Set root directory to `frontend`
   - [ ] Set build command: `npm run build` (default)
   - [ ] Add environment variables (see [frontend/.env.example](../frontend/.env.example))
   - [ ] Set `NEXT_PUBLIC_API_URL` to your backend URL

4. **Verify Deployment**
   - [ ] Run [STAGING_SMOKE_TEST.md](../STAGING_SMOKE_TEST.md) checklist
   - [ ] Test all core flows (speech → feedback → drills)
   - [ ] Test team creation and joining

---

## Required Environment Variables

### Frontend (Next.js)

Set these in your Vercel project or `.env.local`:

```bash
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
NEXT_PUBLIC_API_URL=https://your-backend.onrender.com  # or Railway URL
```

### Backend (FastAPI)

Set these in your Render/Railway project or `.env`:

```bash
OPENAI_API_KEY=sk-...
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
CORS_ORIGINS=https://your-frontend-domain.vercel.app,https://www.your-domain.com
```

⚠️ **Important**: `CORS_ORIGINS` must include all frontend domains (comma-separated, no spaces).

---

## Supabase Setup

### 1. Create a Supabase Project

1. Go to [supabase.com](https://supabase.com) and create a new project
2. Note your project URL and keys from Settings → API
3. You'll need:
   - `NEXT_PUBLIC_SUPABASE_URL`
   - `NEXT_PUBLIC_SUPABASE_ANON_KEY` (for frontend)
   - `SUPABASE_SERVICE_ROLE_KEY` (for backend - keep secret!)

### 2. Apply Database Migrations

Dissio uses SQL migrations in `supabase/migrations/`. Apply them **in order** using the Supabase SQL Editor:

1. Go to your Supabase project → SQL Editor
2. Copy the contents of each migration file and run them in order:
   - `20260524000000_initial_schema.sql`
   - `20260601000000_add_drill_fields.sql`
   - `20260602000000_add_teams.sql`
   - `20260602100000_add_feedback_rating.sql`
   - `20260604000000_add_xp_ledger.sql`

3. Verify tables exist:
   ```sql
   SELECT table_name FROM information_schema.tables 
   WHERE table_schema = 'public';
   ```

   You should see:
   - `profiles`
   - `speeches`
   - `transcripts`
   - `argument_maps`
   - `feedback_reports`
   - `drills`
   - `drill_attempts`
   - `teams`
   - `team_members`
   - `user_xp_events`

### 3. Configure Storage

1. Go to Storage → Create Bucket
2. Bucket name: `audio`
3. Public bucket: ✅ Yes (files will be public URLs)
4. File size limit: 25 MB (recommended)
5. Allowed MIME types: `audio/*`

### 4. Configure Authentication

#### Email Provider

1. Go to Authentication → Providers
2. Enable Email provider
3. Configure email templates (optional but recommended):
   - Customize signup confirmation email
   - Customize password reset email

#### Google OAuth Provider

1. Go to Authentication → Providers → Google
2. Enable Google provider
3. Get Google OAuth credentials:
   - Go to [Google Cloud Console](https://console.cloud.google.com)
   - Create a new project or select existing
   - Go to APIs & Services → Credentials
   - Click "Create Credentials" → "OAuth 2.0 Client ID"
   - Application type: Web application
   - Authorized redirect URIs:
     ```
     https://YOUR_SUPABASE_PROJECT_REF.supabase.co/auth/v1/callback
     ```
     Example: `https://wvfpkhjdpxmvjbdvvimb.supabase.co/auth/v1/callback`
4. Copy Client ID and Client Secret
5. Paste them into Supabase Authentication → Providers → Google configuration

#### URL Configuration

1. Go to Authentication → URL Configuration
   - Set Site URL to your frontend domain: `https://your-app.vercel.app`
   - Add redirect URLs (all required for OAuth to work):
     - **Production**: 
       - `https://your-app.vercel.app/auth/callback`
       - `https://your-app.vercel.app/dashboard`
       - `https://your-app.vercel.app/**`
     - **Local development**:
       - `http://localhost:3000/auth/callback`
       - `http://localhost:3000/dashboard`
       - `http://localhost:3000/**`

⚠️ **Important OAuth Setup**: 
- The `/auth/callback` route is **required** for Google OAuth to work
- Dissio uses browser-side PKCE flow (code verifier stored in cookies via `@supabase/ssr`)
- If you see "PKCE code verifier missing" errors:
  - Verify redirect URLs are configured correctly in Supabase Auth → URL Configuration
  - Ensure `@supabase/ssr` is installed and `createBrowserClient` is used consistently
  - Clear browser cookies and try again
  - Try a different browser (Safari/Chrome privacy settings can interfere)

---

## Frontend Deployment (Vercel)

### Initial Setup

1. Push your code to GitHub
2. Go to [vercel.com](https://vercel.com) → New Project
3. Import your GitHub repository
4. Configure build settings:
   - **Framework Preset**: Next.js
   - **Root Directory**: `frontend`
   - **Build Command**: `npm run build`
   - **Output Directory**: `.next`

5. Add environment variables (Settings → Environment Variables):
   ```
   NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
   NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJ...
   NEXT_PUBLIC_API_URL=https://your-backend.onrender.com
   ```

6. Deploy

### Custom Domain (Optional)

1. Go to Settings → Domains
2. Add your custom domain
3. Update Supabase Auth redirect URLs to include your custom domain

### Redeployment

Vercel auto-deploys on every push to `main`. For manual redeployment:
1. Go to Deployments
2. Click "Redeploy" on the latest deployment

---

## Backend Deployment (Render or Railway)

### Option A: Render

1. Go to [render.com](https://render.com) → New → Web Service
2. Connect your GitHub repository
3. Configure:
   - **Name**: `dissio-api`
   - **Root Directory**: `backend`
   - **Runtime**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Instance Type**: Free or Starter

4. Add environment variables:
   ```
   OPENAI_API_KEY=sk-...
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_SERVICE_ROLE_KEY=service_role_key_here
   CORS_ORIGINS=https://your-frontend.vercel.app
   ```

5. Deploy

6. Copy the backend URL (e.g., `https://dissio-api.onrender.com`) and set it as `NEXT_PUBLIC_API_URL` in Vercel

### Option B: Railway

1. Go to [railway.app](https://railway.app) → New Project → Deploy from GitHub
2. Select your repository
3. Configure:
   - **Root Directory**: `backend`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

4. Add environment variables (same as Render)
5. Generate domain (Settings → Generate Domain)
6. Update `NEXT_PUBLIC_API_URL` in Vercel

---

## CORS Configuration

The backend allows requests from origins listed in the `CORS_ORIGINS` environment variable.

**Production example:**
```bash
CORS_ORIGINS=https://dissio.vercel.app,https://www.dissio.com
```

**Development example:**
```bash
CORS_ORIGINS=http://localhost:3000,http://localhost:8000
```

⚠️ Do not use `*` in production — it allows any origin and is a security risk.

---

## Local Development

### Prerequisites

- Node.js 18+
- Python 3.10+
- Supabase account (or local Supabase via Docker)

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env       # Then fill in your keys
uvicorn app.main:app --reload
```

Backend runs at `http://localhost:8000`.

### Frontend

```bash
cd frontend
npm install
cp .env.example .env.local  # Then fill in your keys
npm run dev
```

Frontend runs at `http://localhost:3000`.

---

## Production Smoke Test Checklist

After deploying to production, test these flows manually.

For staging deployments, see **[STAGING_SMOKE_TEST.md](./STAGING_SMOKE_TEST.md)** for a detailed step-by-step checklist.

### Student Flow
- ✅ Sign up with email
- ✅ Sign in
- ✅ Create a new speech
- ✅ Record or upload audio (30-90 seconds recommended)
- ✅ Transcribe speech
- ✅ Generate flow (argument map)
- ✅ Generate feedback
- ✅ View feedback scores and weaknesses
- ✅ Generate drills
- ✅ Record a drill attempt
- ✅ View progress dashboard

### Team Flow
- ✅ Create a team
- ✅ Copy invite code
- ✅ Join team using invite code (from a second account)
- ✅ Coach views team dashboard
- ✅ Coach sees student progress

### Edge Cases
- ✅ Upload very short audio (<10 seconds) — should show appropriate error
- ✅ Try to access another user's speech URL directly — should return 404
- ✅ Sign out and sign back in — data persists

---

## Troubleshooting

### Frontend can't reach backend

**Symptom**: "Could not load your data. Please refresh and try again."

**Fix**:
1. Check that `NEXT_PUBLIC_API_URL` is set correctly in Vercel
2. Verify backend is running (visit `https://your-backend.onrender.com/health`)
3. Check CORS settings — frontend domain must be in `CORS_ORIGINS`

### Authentication errors

**Symptom**: User gets redirected to login repeatedly

**Fix**:
1. Check Supabase Auth → URL Configuration
2. Make sure Site URL matches your frontend domain
3. Add redirect URL: `https://your-app.vercel.app/**`

### Audio upload fails

**Symptom**: "Upload failed" error when recording or uploading

**Fix**:
1. Check Supabase Storage → `audio` bucket exists
2. Verify bucket is public
3. Check file size limits (default 25 MB)
4. Verify `NEXT_PUBLIC_SUPABASE_ANON_KEY` is correct

### AI generation fails

**Symptom**: "Transcription failed" / "Flow generation failed"

**Fix**:
1. Check `OPENAI_API_KEY` is set in backend
2. Verify OpenAI API key has credits
3. Check backend logs (Render/Railway dashboard)

### Database connection errors

**Symptom**: Backend crashes or returns 500 errors

**Fix**:
1. Verify `SUPABASE_URL` is correct
2. Verify `SUPABASE_SERVICE_ROLE_KEY` is the **service role key**, not anon key
3. Check Supabase project status (Settings → General)

---

## Security Notes

- **Never commit `.env` files** — use `.env.example` as a template
- **Service role key** is secret — only use it on the backend, never expose to frontend
- **CORS** must be configured for production domains only
- **Supabase RLS** is bypassed by service role key — backend handles access control

---

## Support

For deployment issues:
- Check backend logs (Render/Railway dashboard)
- Check frontend logs (Vercel dashboard → Logs)
- Check Supabase logs (Supabase dashboard → Logs)

For questions, contact: yashnilmohanty@gmail.com
