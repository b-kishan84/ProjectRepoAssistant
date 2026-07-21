# 🚀 Ultimate Deployment Guide for Full-Stack Python Projects

This guide will walk you through deploying a full-stack Python application (like FastAPI + Streamlit) to the cloud. You can use this guide as a reference for deploying any of your GitHub repositories.

## 🌟 Recommended Cloud Platforms

For Python-based projects (FastAPI, Streamlit, Flask, Django), the most developer-friendly and cost-effective platforms are:

1. **[Render](https://render.com/)** (Recommended for both Backend and Frontend)
2. **[Railway](https://railway.app/)** (Great alternative with a seamless GitHub integration)
3. **[Streamlit Community Cloud](https://share.streamlit.io/)** (Best for standalone Streamlit apps)

---

## 🛠️ Prerequisites Before Deploying

Before deploying any project from GitHub, ensure your repository has the following:

1. **`requirements.txt`**: A file listing all your Python dependencies.
   - *If you don't have one, generate it locally: `pip freeze > requirements.txt`*
2. **`README.md`**: Good practice to document your project.
3. **`.gitignore`**: Ensure you are not pushing `.env`, `__pycache__`, or `.venv` to GitHub.
4. **Environment Variables**: Know which secrets/API keys your app needs (e.g., `GEMINI_API_KEY`).

---

## 🏗️ Step 1: Deploying the Backend (FastAPI) on Render

We will use **Render** to deploy the FastAPI backend because it has a generous free tier and connects directly to GitHub.

### 1. Create a Web Service
1. Go to [Render Dashboard](https://dashboard.render.com/) and click **New > Web Service**.
2. Select **Build and deploy from a Git repository**.
3. Connect your GitHub account and select this repository.

### 2. Configure the Service
- **Name**: `my-project-backend`
- **Language**: `Python 3`
- **Branch**: `main`
- **Root Directory**: Leave blank (or set to `./` depending on where requirements.txt is).
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `uvicorn backend.main:app --host 0.0.0.0 --port 10000` *(Adjust `backend.main:app` based on where your FastAPI instance is defined)*

### 3. Add Environment Variables
1. Scroll down to **Environment Variables**.
2. Add any keys your backend needs (e.g., Database URLs, API keys).
3. Click **Create Web Service**.

Render will now build and deploy your API. Once finished, you will get a URL like `https://my-project-backend.onrender.com`.

---

## 🎨 Step 2: Deploying the Frontend (Streamlit)

You can deploy the Streamlit frontend either on **Streamlit Community Cloud** (easiest for Streamlit) or **Render**.

### Option A: Streamlit Community Cloud (Easiest)
1. Go to [Streamlit Community Cloud](https://share.streamlit.io/) and log in with GitHub.
2. Click **New app**.
3. Select your repository and branch.
4. **Main file path**: Enter `frontend/app.py`
5. Click **Advanced settings** to add your Environment Variables (like your new Backend API URL: `BACKEND_URL=https://my-project-backend.onrender.com`).
6. Click **Deploy!**

### Option B: Deploying Frontend on Render
1. Go to [Render Dashboard](https://dashboard.render.com/) > **New > Web Service**.
2. Select your repository again.
3. **Name**: `my-project-frontend`
4. **Build Command**: `pip install -r requirements.txt`
5. **Start Command**: `streamlit run frontend/app.py --server.port $PORT --server.address 0.0.0.0`
6. **Environment Variables**: Add `BACKEND_URL` pointing to your deployed backend API.
7. Click **Create Web Service**.

---

## 🔗 Step 3: Connecting Frontend and Backend

Once both are deployed, they need to talk to each other.

1. Ensure your **Frontend** is using the deployed Backend URL, not `localhost`.
   - Instead of `requests.get("http://localhost:8000/endpoint")`
   - Use `requests.get(f"{os.getenv('BACKEND_URL')}/endpoint")`
2. Update your **Backend CORS settings**. FastAPI needs to allow requests from your deployed frontend domain.
   ```python
   from fastapi.middleware.cors import CORSMiddleware
   
   app.add_middleware(
       CORSMiddleware,
       allow_origins=["https://your-streamlit-app-url.com"], # Add your frontend URL here
       allow_credentials=True,
       allow_methods=["*"],
       allow_headers=["*"],
   )
   ```
   *(Commit and push this change to GitHub to trigger a redeploy on Render)*

---

## 💡 Best Practices for Future Projects

- **Keep Secrets Secret**: Never push `.env` files. Always use the hosting provider's Dashboard to enter Environment Variables.
- **Auto-Deploys**: By default, Render and Streamlit Cloud will automatically redeploy whenever you push new commits to the `main` branch.
- **Port Binding**: Cloud providers assign dynamic ports. Always use `0.0.0.0` for host addresses in Python, and read the `$PORT` environment variable if required by the provider.
