# Deployment Guide

How to deploy LLM Cost Firewall to production.

---

## Quick Deploy Options

### Option 1: Render.com (Recommended - Free Tier)

**Steps:**

1. **Fork this repo** on GitHub

2. **Go to [Render.com](https://render.com)** and sign in

3. **Create New Web Service**
   - Connect your GitHub repo
   - Name: `llm-cost-firewall`
   - Environment: `Python 3`
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

4. **Add Environment Variables:**
   ```
   GEMINI_API_KEY=your-api-key-here
   MOCK_MODE=false
   ```

5. **Deploy!** (takes ~5 minutes)

**Your app will be at:** `https://llm-cost-firewall.onrender.com`

**Free Tier Limits:**
- ✅ 750 hours/month free
- ✅ Automatic HTTPS
- ⚠️ Sleeps after 15 min inactivity
- ⚠️ 512MB RAM limit

---

### Option 2: Railway.app (Free $5 Credit)

**Steps:**

1. **Go to [Railway.app](https://railway.app)** and sign in with GitHub

2. **New Project** → **Deploy from GitHub repo**

3. **Select your fork** of llm-cost-firewall

4. **Add Variables:**
   ```
   GEMINI_API_KEY=your-api-key-here
   ```

5. **Railway auto-detects** Python and deploys

**Your app:** `https://llm-cost-firewall-production.up.railway.app`

**Free Tier:**
- ✅ $5 free credit/month
- ✅ Always-on (no sleep)
- ✅ 8GB RAM available
- ⚠️ Credit expires after usage

---

### Option 3: Fly.io (Free Tier)

**Steps:**

1. **Install Fly CLI:**
   ```bash
   curl -L https://fly.io/install.sh | sh
   ```

2. **Login:**
   ```bash
   fly auth login
   ```

3. **Launch app:**
   ```bash
   fly launch
   ```

4. **Set secrets:**
   ```bash
   fly secrets set GEMINI_API_KEY=your-api-key-here
   ```

5. **Deploy:**
   ```bash
   fly deploy
   ```

**Your app:** `https://llm-cost-firewall.fly.dev`

---

## Docker Deployment

### Create Dockerfile

```dockerfile
FROM python:3.10-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app
COPY app/ ./app/

# Expose port
EXPOSE 8000

# Run server
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Build and Run

```bash
# Build image
docker build -t llm-cost-firewall .

# Run container
docker run -d \
  -p 8000:8000 \
  -e GEMINI_API_KEY=your-api-key \
  llm-cost-firewall
```

### Docker Compose

```yaml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - GEMINI_API_KEY=${GEMINI_API_KEY}
      - MOCK_MODE=false
    volumes:
      - ./logs:/app/logs
      - ./models:/app/models
    restart: unless-stopped
```

Run: `docker-compose up -d`

---

## Cloud Platform Deployment

### AWS (EC2 + Elastic Beanstalk)

1. **Create `Procfile`:**
   ```
   web: uvicorn app.main:app --host 0.0.0.0 --port $PORT
   ```

2. **Deploy:**
   ```bash
   eb init -p python-3.10 llm-cost-firewall
   eb create llm-cost-firewall-env
   eb setenv GEMINI_API_KEY=your-key
   eb deploy
   ```

### Google Cloud (Cloud Run)

1. **Create `cloudbuild.yaml`:**
   ```yaml
   steps:
     - name: 'gcr.io/cloud-builders/docker'
       args: ['build', '-t', 'gcr.io/$PROJECT_ID/llm-firewall', '.']
   images:
     - 'gcr.io/$PROJECT_ID/llm-firewall'
   ```

2. **Deploy:**
   ```bash
   gcloud builds submit --config cloudbuild.yaml
   gcloud run deploy llm-firewall \
     --image gcr.io/$PROJECT_ID/llm-firewall \
     --set-env-vars GEMINI_API_KEY=your-key
   ```

### Azure (Container Instances)

```bash
az container create \
  --resource-group myResourceGroup \
  --name llm-firewall \
  --image your-docker-image \
  --cpu 1 \
  --memory 1 \
  --ports 8000 \
  --environment-variables GEMINI_API_KEY=your-key
```

---

## 🔧 Production Configuration

### Environment Variables

```bash
# Required
GEMINI_API_KEY=your-api-key-here

# Optional
MOCK_MODE=false
DAILY_BUDGET_USD=100
HOURLY_BUDGET_USD=10
```

### Logging

**Development:**
```bash
# Stdout logging
python app/main.py
```

**Production:**
```python
# In app/main.py, add:
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)
```

### Monitoring

Add health check endpoint (already included):
```bash
GET /
```

Returns:
```json
{
  "status": "running",
  "message": "LLM Cost Firewall is active"
}
```

**Set up monitoring:**
- Uptime check every 5 minutes
- Alert if response > 5 seconds
- Alert if status != 200

---

## Security Checklist

- [ ] ✅ API key in environment variables (not code)
- [ ] ✅ HTTPS enabled (automatic on Render/Railway)
- [ ] ✅ Rate limiting configured
- [ ] ⚠️ Add authentication for production use
- [ ] ⚠️ Set up CORS for frontend
- [ ] ⚠️ Enable API key rotation

### Add Authentication (Optional)

```python
from fastapi import Header, HTTPException

async def verify_token(x_api_key: str = Header(...)):
    if x_api_key != os.getenv("API_SECRET"):
        raise HTTPException(status_code=401, detail="Invalid API key")

# Add to endpoints:
@app.post("/chat", dependencies=[Depends(verify_token)])
```

---

## Performance Tuning

### Increase Workers (Production)

```bash
# Use Gunicorn for multiple workers
pip install gunicorn

# Run with 4 workers
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### Redis for Distributed Caching

```python
# Install redis
pip install redis

# Update cache.py
import redis
cache_client = redis.Redis(host='localhost', port=6379, db=0)
```

---

## Pre-Deployment Testing

**Run all tests:**
```bash
# Health check
curl https://your-app.com/

# Test query
curl -X POST https://your-app.com/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "user_id": "test"}'

# Check stats
curl https://your-app.com/stats
```

---

## Scaling Strategy

### Small (0-1K req/day)
- ✅ Free tier (Render/Railway)
- ✅ In-memory caching
- ✅ Single instance

### Medium (1K-100K req/day)
- Use paid tier ($7-20/month)
- Add Redis caching
- 2-3 instances with load balancer

### Large (100K+ req/day)
- Dedicated servers
- Redis cluster
- Auto-scaling (5-20 instances)
- CDN for static content

---

## Troubleshooting

**App won't start:**
```bash
# Check logs
render logs
# or
railway logs
# or
fly logs
```

**High latency:**
- Check Gemini API rate limits
- Add Redis caching
- Increase worker count

**Out of memory:**
- Reduce cache size
- Upgrade tier
- Implement cache eviction

---

## Post-Deployment

1. **Test all endpoints** with production URL
2. **Set up monitoring** (UptimeRobot/Pingdom)
3. **Add to portfolio** with live demo link
4. **Update README** with deployment URL
5. **Share on LinkedIn** 🎉

---

**Need help?** Open an issue on GitHub!