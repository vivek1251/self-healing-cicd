# 🤖 Self-Healing CI/CD Pipeline

A production-grade DevOps project that automatically detects failures, diagnoses issues using **Gemini AI**, and self-restarts — with real-time **Slack alerts**.

**Live App:** http://<your-ec2-ip>:5000

---

## 🏗️ Architecture
```
Developer pushes code
        ↓
GitHub Actions CI/CD
        ↓
Docker Build & Push to DockerHub
        ↓
Auto-Deploy to AWS EC2
        ↓
Self-Healing Monitor (heal.py)
        ↓
App crashes? → Gemini AI diagnoses → Auto-restart → Slack alert
```

---

## 🚀 Features

- ✅ **Flask REST API** with `/health` endpoint
- ✅ **Dockerized** application
- ✅ **DockerHub** image registry
- ✅ **GitHub Actions** CI/CD pipeline — auto-deploys on every `git push`
- ✅ **AWS EC2** cloud deployment
- ✅ **Self-Healing Monitor** — detects crashes and auto-restarts
- ✅ **Gemini AI Diagnosis** — AI analyzes logs and explains what went wrong
- ✅ **Slack Alerts** — real-time notifications for every event

---

## 📁 Project Structure
```
self-healing-cicd/
├── app/
│   ├── app.py              # Flask application
│   └── Dockerfile          # Docker configuration
├── scripts/
│   └── heal.py             # Self-healing monitor with Gemini AI
├── .github/
│   └── workflows/
│       └── deploy.yml      # GitHub Actions CI/CD pipeline
└── README.md
```

---

## 🛠️ Tech Stack

| Technology | Purpose |
|------------|---------|
| Python + Flask | REST API |
| Docker | Containerization |
| DockerHub | Image Registry |
| GitHub Actions | CI/CD Pipeline |
| AWS EC2 | Cloud Server |
| Google Gemini AI | Intelligent Log Diagnosis |
| Slack Webhooks | Real-time Alerts |

---

## ⚙️ Setup & Installation

### Prerequisites
- AWS account with EC2 instance running
- DockerHub account
- GitHub account
- Google Gemini API key ([Get one here](https://aistudio.google.com))
- Slack webhook URL

### 1. Clone the Repository
```bash
git clone https://github.com/vivek1251/self-healing-cicd.git
cd self-healing-cicd
```

### 2. Configure GitHub Secrets
Go to **Settings → Secrets and variables → Actions** and add:

| Secret | Value |
|--------|-------|
| `EC2_HOST` | Your EC2 public IP |
| `EC2_USER` | `ubuntu` |
| `EC2_KEY` | Your PEM key (base64 encoded) |
| `DOCKER_USERNAME` | Your DockerHub username |
| `DOCKER_PASSWORD` | Your DockerHub password |
| `GEMINI_API_KEY` | Your Gemini API key |

### 3. Deploy
Simply push to main branch — GitHub Actions handles everything:
```bash
git push origin main
```

### 4. Run the Self-Healing Monitor on EC2
```bash
ssh -i your-key.pem ubuntu@your-ec2-ip
export GEMINI_API_KEY="your-key"
nohup python3 ~/heal.py > ~/heal.log 2>&1 &
```

---

## 🔄 How Self-Healing Works

1. `heal.py` checks `/health` endpoint every **10 seconds**
2. After **3 consecutive failures**, it triggers healing
3. **Gemini AI** analyzes the last 20 lines of Docker logs
4. Sends an AI-generated diagnosis to **Slack**
5. **Auto-restarts** the Docker container
6. Sends a recovery confirmation to Slack

---

## 🧪 Testing Self-Healing

SSH into your EC2 server and manually stop the app:
```bash
docker stop myapp && docker rm myapp
```

Watch Slack for:
- 🔴 App is DOWN alert
- 🤖 Gemini AI Diagnosis
- ⚙️ Auto-restarting...
- 🟢 App AUTO-RESTARTED and healthy!

---

## 📊 CI/CD Pipeline

The GitHub Actions pipeline runs on every push to `main`:

1. **Checkout** code
2. **Build** Docker image
3. **Push** to DockerHub
4. **Deploy** to EC2 via SSH
5. App is live! 🚀

---

## 🌐 API Endpoints

| Endpoint | Method | Response |
|----------|--------|----------|
| `/health` | GET | `{"status": "healthy"}` |

---

## 👨‍💻 Author

**Vivek Bommalla**
- GitHub: [@vivek1251](https://github.com/vivek1251)
- DockerHub: [vivekbommalla1251](https://hub.docker.com/u/vivekbommalla1251)

---

## 📄 License

MIT License — feel free to use this project as a template!
