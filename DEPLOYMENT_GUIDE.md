# 🚀 MITRA Deployment Guide — Vercel + Render

**MITRA — Autonomous AI Teammate for Paytm Merchants**  
*Paytm Build for India AI Hackathon – Delhi Edition (Track 3 — Autonomous AI Teammates)*  
**Team:** Pica pica  
**Repository:** [https://github.com/AmitNIET159/mitra-autonomous-ai](https://github.com/AmitNIET159/mitra-autonomous-ai)

---

## 🏛 Architecture Overview

| Component | Platform | Tech Stack | Root Directory | Default URL |
| :--- | :--- | :--- | :--- | :--- |
| **Backend API** | **Render** | FastAPI, Python 3.11, SQLite | `backend` | `https://mitra-backend.onrender.com` |
| **Frontend UI** | **Vercel** | Next.js 16, React 19, Tailwind v4 | `frontend` | `https://mitra-autonomous-ai.vercel.app` |

MITRA's backend automatically initializes and seeds a 520-customer deterministic digital-twin database upon cold start if no database exists, ensuring the live demo is immediately operational with zero manual database provisioning.

---

## 🛠 Step 1: Deploy Backend to Render (Free)

Deploying the backend takes ~3 minutes.

### Method A — Using Render Blueprint (Recommended, 1-Click)

1. Log in to [Render Dashboard](https://dashboard.render.com/).
2. Click **New +** → **Blueprint**.
3. Connect your GitHub account and select repository: **`AmitNIET159/mitra-autonomous-ai`**.
4. Render will automatically detect the [`render.yaml`](../render.yaml) file at the repository root.
5. (Optional) Provide your `GEMINI_API_KEY` when prompted, or leave it blank (MITRA will use its deterministic fallback reasoner).
6. Click **Apply**.
7. Once deployed, copy your service URL (e.g., `https://mitra-backend-xxxx.onrender.com`).

---

### Method B — Manual Web Service Setup

If you prefer to configure manually:

1. In Render Dashboard, click **New +** → **Web Service**.
2. Select **`AmitNIET159/mitra-autonomous-ai`**.
3. Configure the following settings:
   - **Name**: `mitra-backend`
   - **Region**: Singapore or Frankfurt (any region is fine)
   - **Branch**: `main`
   - **Root Directory**: `backend`
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Instance Type**: `Free`
4. Add **Environment Variables** (under *Advanced* or *Environment* tab):
   | Key | Value | Description |
   | :--- | :--- | :--- |
   | `PYTHON_VERSION` | `3.11.9` | Python runtime version |
   | `SIMULATION_MODE` | `true` | Enforces digital-twin safety sandbox |
   | `CORS_ORIGINS` | `*` | Allows Vercel frontend requests |
   | `APP_ENV` | `production` | Production mode |
   | `AI_PROVIDER_PREFERENCE` | `auto` | Auto-detects Gemini / Hugging Face / Fallback |
   | `GEMINI_API_KEY` | *(your Gemini key)* | Optional; get from [Google AI Studio](https://aistudio.google.com/) |
5. Click **Create Web Service**.
6. Wait for the build and deployment logs to say `Application startup complete`.
7. Copy your backend URL: e.g. `https://mitra-backend.onrender.com`.

---

## ⚡ Step 2: Deploy Frontend to Vercel (Free)

Deploying the frontend takes ~1 minute.

1. Log in to [Vercel Dashboard](https://vercel.com/new).
2. Click **Add New...** → **Project**.
3. Import Git Repository: **`AmitNIET159/mitra-autonomous-ai`**.
4. Under **Configure Project**:
   - **Project Name**: `mitra-autonomous-ai` (or your preferred name)
   - **Framework Preset**: `Next.js` (automatically detected)
   - **Root Directory**: Click **Edit** and select **`frontend`** (🚨 **CRITICAL**: Do NOT leave as root `/`)
5. Under **Environment Variables**, add:
   - **Name**: `NEXT_PUBLIC_API_URL`
   - **Value**: Your Render Backend URL from Step 1 (e.g. `https://mitra-backend.onrender.com` — *no trailing slash*)
6. Click **Deploy**.
7. Vercel will build and deploy your application. Within 60 seconds, you will receive a production URL (e.g. `https://mitra-autonomous-ai.vercel.app`).

---

## ✅ Step 3: Verification Checklist

Once both services are deployed, verify the system end-to-end:

1. **Verify Backend Health**:
   - Open: `https://<YOUR_RENDER_URL>/api/health`
   - Expected response: `{"status":"ok","service":"MITRA","version":"0.1.0"}`
2. **Verify Digital Twin Seeding**:
   - Open: `https://<YOUR_RENDER_URL>/api/system/status`
   - Expected response: `merchant_profile` populated with `"Sharma Kirana & General Store"` and 520 customers seeded.
3. **Verify Interactive Command Center**:
   - Open your Vercel URL in a desktop browser.
   - You should see the **MITRA Autonomous AI Command Center** with live health metrics, customer segments, soundbox status, and autonomy controls.
4. **Trigger a Live Autonomous Scenario**:
   - Click the **Demo Scenario Controller** dropdown (e.g. *Inactive Customer Churn Winback*).
   - Click **Run Scenario**.
   - Watch MITRA autonomously:
     1. Detect signal
     2. Conduct 4-phase investigation
     3. Generate guardrailed decision
     4. Enforce execution barrier
     5. Dispatch simulated campaign
     6. Learn and project business impact (GMV recovery, ROI)
5. **Test Reset**:
   - Click **Reset Scenario** to wipe transient state back to pristine demo conditions.

---

## 🔒 Security & Sandbox Guarantees

- **No Real Funds at Risk**: All disbursements, Paytm Soundbox alerts, and merchant campaigns execute in MITRA's `SIMULATION_MODE=true` deterministic digital twin sandbox.
- **Fail-Safe Autonomy**: If Gemini LLM is unconfigured, rate-limited, or fails, the deterministic fallback client activates instantly with 0 ms downtime.
- **Strict Guardrails**: Hard limits enforce maximum INR ₹5,000 budget, max 25% discount, and max 5 daily actions regardless of AI autonomy level.
