# Orca - Vibe-Coding Machine Learning Platform

Orca is a platform for vibe-coding machine learning — a conversational way to build and evolve models without writing a single line of boilerplate code. Instead of switching between notebooks, terminals, and documentation, you simply chat. Give Orca your dataset and describe what you want to achieve — classification, regression, image generation, anything — and it automatically constructs the entire pipeline from preprocessing to training, evaluation, and optimization.

## Architecture

- **Frontend**: Next.js + TypeScript (handles chat, LLM, code generation, UI)
- **Backend**: Python FastAPI (executes ML code in isolated Docker containers)
- **Execution**: Docker container per user with Jupyter kernel inside
- **Scalability**: Redis queue + worker pool for handling 1000s of users

## Project Structure

```
orca/
├── backend/              # FastAPI backend (code execution only)
├── frontend/            # Next.js frontend (all business logic)
├── docker/              # Docker images and configs
├── workspace/           # User data storage (gitignored)
└── README.md
```

## Getting Started

### Prerequisites

- Python 3.10+
- Node.js 18+
- Docker & Docker Compose
- Redis (for scalability, optional for MVP)

### Development Setup

1. **Backend Setup:**
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Frontend Setup:**
   ```bash
   cd frontend
   npm install
   ```

3. **Environment Variables:**
   - Copy `.env.example` to `.env` and `.env.local`
   - Add your OpenAI API key and backend URL

4. **Run Locally:**
   ```bash
   # Terminal 1: Backend
   cd backend
   uvicorn main:app --reload

   # Terminal 2: Frontend
   cd frontend
   npm run dev
   ```

## Development Status

🚧 Under active development

## License

MIT

