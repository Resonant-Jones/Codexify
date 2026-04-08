# Codexify Setup Instructions with Setup Wizard

This guide walks you through the complete setup process for Codexify using the interactive setup wizard, from installing prerequisites to sending your first message.

## Prerequisites

Before starting the setup, you'll need to install these dependencies:

### 1. Docker Installation
- **Windows/macOS**: Install [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- **Linux**: Install [Docker Engine](https://docs.docker.com/engine/install/)
- Verify installation: `docker --version`

### 2. Local LLM Option (Choose One)

#### Option A: Ollama (Recommended for Local Use)
- Install Ollama from [ollama.com](https://ollama.com/download)
- Pull a model (e.g., `ollama pull llama3.2`)
- Verify installation: `ollama list`

> **Note**: Skip Ollama installation if you plan to use cloud-based LLMs (Claude/ChatGPT) instead

#### Option B: Cloud API Keys (Alternative to Local Models)
- **Claude API Key**: Create an account at [Anthropic Console](https://console.anthropic.com/) and obtain your API key
- **OpenAI API Key**: Create an account at [OpenAI Platform](https://platform.openai.com/) and obtain your API key

> **Important**: If your hardware cannot run Ollama (due to memory, CPU, or GPU limitations), you must use Option B with cloud-based API keys

## Installation Steps

### Step 1: Clone the Repository
```bash
git clone https://github.com/Codexify/Codexify.git
cd Codexify
```

### Step 2: Run the Setup Wizard
```bash
# Install the project in development mode (includes setup wizard)
pip install -e .

# Run the setup wizard
python -m guardian.cli.memoryos_cli setup
```

### Step 3: Choose Setup Mode
The setup wizard offers two modes:

#### Fast Setup (Recommended for First Time)
- Quickly gets you running with minimal configuration
- Automatically detects installed dependencies (Docker, Ollama)
- Sets up basic environment variables

#### Custom Setup (Advanced)
- Provides detailed configuration options
- Allows custom binary paths for Docker/Ollama
- Configures connectors (Notion, GitHub)
- Selects runtime profiles (Docker vs external services)

### Step 4: Configure Your LLM Provider

During the setup, you'll be prompted to configure your LLM provider:

#### For Local Models with Ollama:
- Ensure Ollama is running (`ollama serve` in a separate terminal)
- The wizard will automatically configure:
  - `LLM_PROVIDER=local`
  - `LOCAL_BASE_URL=http://localhost:11434`
  - Select your preferred model (e.g., `LOCAL_CHAT_MODEL=llama3.2`)

#### For Cloud-based Models:
- Enter your API key when prompted
- Select your preferred provider:
  - For Claude: `LLM_PROVIDER=anthropic`, `ANTHROPIC_API_KEY=your_key_here`
  - For ChatGPT: `LLM_PROVIDER=openai`, `OPENAI_API_KEY=your_key_here`

### Step 5: Configure Additional Settings
- **Cloud Providers**: Enable if you want to use cloud services (default: enabled)
- **Connectors**: Optionally configure Notion or GitHub connectors
- **Runtime Profile**: Choose between Docker (recommended) or external services

### Step 6: Complete Setup
- The wizard will generate a `.env` file in the project root
- Review the generated configuration values
- The setup is complete when you see: "Wrote .env"

## Starting Codexify

After setup is complete:

### Method 1: Docker Compose (Recommended)
```bash
# Start all services
docker compose up

# Or to run in background
docker compose up -d

# Services will be available at:
# - Backend API: http://localhost:8888
# - Frontend UI: http://localhost:5173
```

### Method 2: Individual Services (Development)
```bash
# Terminal 1: Start the backend
python -m guardian.cli.memoryos_cli backend

# Terminal 2: Start the frontend
cd frontend && npm run dev
```

## Sending Your First Message

1. Open your browser and navigate to [http://localhost:5173](http://localhost:5173)
2. The Codexify interface will load and connect to your configured LLM provider
3. Start a new conversation in the chat interface
4. Type your first message and press Enter
5. Wait for the response from your selected LLM

## Troubleshooting

### Common Issues and Solutions:

#### 1. Docker Permission Error
```bash
# Add user to docker group (Linux)
sudo usermod -aG docker $USER
# Then log out and log back in
```

#### 2. Ollama Not Found
- Ensure Ollama service is running: `ollama serve`
- Check that the service is accessible at http://localhost:11434
- Restart Ollama if needed

#### 3. Database Connection Issues
- Make sure all Docker services are running: `docker ps`
- Check that PostgreSQL container has started successfully
- Look for any errors in the Docker logs: `docker compose logs db`

#### 4. API Key Not Working
- Verify your API key is correctly entered in `.env`
- Check that your cloud provider is properly enabled
- Confirm your account has sufficient credits/access

### Run Diagnostics
```bash
# Check your configuration
python -m guardian.cli.memoryos_cli doctor
```

## Next Steps

- Explore the Codexify documentation in the `/docs` directory
- Customize your configuration in the `.env` file
- Configure additional connectors (Notion, GitHub) through the wizard
- Try out different LLM providers based on your needs
- Review the security configuration in `CONFIGURATION.md`

## Hardware Requirements

- **Minimum**: 8GB RAM, 4 CPU cores, 10GB free disk space
- **Recommended**: 16GB+ RAM, 8+ CPU cores, SSD storage
- **For Ollama**: Sufficient VRAM/RAM to run your selected model locally

> **Note**: If your hardware cannot meet requirements for local models, using cloud-based LLMs with API keys is the recommended alternative.

## Support

If you encounter issues:
1. Run the doctor command: `python -m guardian.cli.memoryos_cli doctor`
2. Check the [official documentation](https://github.com/Codexify/Codexify/tree/main/docs)
3. Create an issue in the GitHub repository with detailed system information and error logs
