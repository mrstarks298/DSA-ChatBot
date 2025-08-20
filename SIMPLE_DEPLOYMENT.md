# 🚀 Simple Render Deployment

## ✅ **Simplified Configuration**

I've removed all extra files and kept only what Render needs:

- ✅ **requirements.txt** - Only Python dependencies
- ✅ **Procfile** - Simple gunicorn command
- ✅ **run.py** - Flask app entry point

## 🔧 **Render Setup**

### **1. Create Web Service:**
- Connect your GitHub repository
- Choose "Web Service"
- Select your repository

### **2. Configure:**
- **Name:** `dsa-chatbot`
- **Environment:** `Python 3`
- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `gunicorn run:app`

### **3. Environment Variables:**
```bash
FLASK_CONFIG=production
FLASK_SECRET_KEY=your-secret-key
SUPABASE_URL=https://tsuwpbunvavtygtnsypm.supabase.co
SUPABASE_KEY=your-supabase-key
GROQ_API_KEY=your-groq-key
HF_API_TOKEN=your-huggingface-token
HF_API_TOKEN_BACKUP=your-backup-token
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
REDIRECT_URI=https://your-domain.onrender.com/oauth2callback
```

## 🎯 **That's It!**

Render will:
1. Read `requirements.txt` for dependencies
2. Use `Procfile` for startup command
3. Run your Flask app

**No extra configuration files needed! 🎉**
