# Boost Papers Agent

**🌐 Language | 言語:** **English** | [日本語](README_JP.md)

> **Note:** This English version contains the most accurate and up-to-date information.

A powerful AI agent for analyzing academic papers, extracting insights, and discovering related research using advanced language models and PDF processing capabilities.

## 🚀 Features

- **PDF Processing**: Extract and analyze text from PDF files and URLs
- **AI-Powered Summarization**: Generate comprehensive paper summaries using state-of-the-art LLMs
- **Related Paper Discovery**: Find semantically similar research papers
- **Slack Integration**: Seamless integration with Slack for team collaboration
- **3D Visualization**: Interactive visualization of paper embeddings and correlations
- More...?

## 🛠️ Setup

### Option 1: Dify Cloud Service (Recommended)

1. **Create Account**
   - Visit [Dify Cloud](https://cloud.dify.ai/apps) and register an account

2. **Configure Plugins**
   - Navigate to **Settings** → **Plugins**
   - Install the following plugins:
     - `Jina AI`
     - `Gemini` 
     - `OpenAI`
     - `Slack Bot`

3. **Setup API Keys**
   - **OpenAI/Gemini**: Go to **Settings** → **Model Provider** and enter your API key
   - **Jina AI**: Obtain API key from [jina.ai](https://jina.ai/), then configure in the plugin's Authorization field

4. **Import Agent**
   - Go to **Studio** tab
   - Click **Import DSL file** and upload `dify_dsl/boost-papers-agent.yaml`

### Option 2: Local Dify Server

1. **Install Docker**
   - **Ubuntu**: Follow [Docker Engine installation guide](https://docs.docker.com/engine/install/ubuntu/)
   - **macOS/Windows**: Download [Docker Desktop](https://www.docker.com/products/docker-desktop)

2. **Deploy Dify**
   ```bash
   git clone https://github.com/langgenius/dify.git
   cd dify/docker
   cp .env.example .env
   sudo docker compose up -d
   ```

3. **Access & Configure**
   - Open `http://localhost` in your browser
   - Create account and follow steps 2-4 from Option 1 above

## 🎯 Dify App Usage

Once you've completed the setup:

1. **Publish the App**
   - In Dify, click the **Publish** button
   - Configure your publishing settings as needed
   - Confirm the publication

2. **Start Using the Agent**
   - Click **Run App** to open the chat interface
   - Upload a PDF file or provide a PDF URL
   - Ask questions about the paper or request summaries
   - Discover related research papers

## 📋 Development Status

- [x] PDF URL input processing
- [x] PDF file upload support
- [x] Text extraction from PDFs
- [x] LLM-powered paper summarization
- [x] Related paper discovery
- [ ] Allow follow-up questions about the paper
- [ ] Deploy to AWS/GCP
- [ ] Slack integration (might need AWS/GCP setup)
- [ ] PDF embeddings visualization
- [ ] Enhanced error handling
- [ ] Use Python to discover related papers instead?

*Feel free to contribute by adding more features!*

## 🔬 PDF Embeddings Visualization

*Work in progress: Interactive 3D visualization of PDF semantic correlations using PyTorch sentence embeddings.*

### Prerequisites
```bash
conda create -n boost-proj python=3.12
conda activate boost-proj
pip install -r requirements.txt
```

### Usage

**Generate Embeddings:**
```bash
python pdf_correlator.py
```

**Visualize Results:**
```bash
tensorboard --logdir tensorboard_logs
```

## 🤝 Contributing

Please feel free to:
- Report bugs
- Suggest new features
- Submit pull requests
- Improve documentation

