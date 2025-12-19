# Tammi Education Agent

LangGraph-based education agent for learning resource management, exercise creation, and study guidance.

## Features

- **Search Material**: Find educational resources and learning materials
- **Create Exercise**: Generate exercises and quizzes for different subjects
- **Correct Exercise**: Check and correct homework with detailed explanations
- **Tutor Subject**: Provide study guidance and learning methods

## Intents and Sub-intents

### Intent: `learning_resource`
- **search_material**: Tìm kiếm tài liệu học tập
  - Example: "Tìm tài liệu học python cơ bản"
- **create_exercise**: Tạo bài tập hoặc câu hỏi
  - Example: "Tạo bài tập trắc nghiệm tiếng anh lớp 10"

### Intent: `study_guidance`
- **correct_exercise**: Chữa bài tập, sửa lỗi
  - Example: "Giúp tôi chữa bài toán này"
- **tutor_subject**: Hướng dẫn học ngoại ngữ và các môn học
  - Example: "Trẻ lớp 5 nên học tiếng anh thế nào"

## Quick Start

### Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Configure environment
cp env-config.secret.yaml.example env-config.secret.yaml
# Edit env-config.secret.yaml with your API keys
```

### Run HTTP Server

```bash
python -m agent.entrypoint.run
```

The server will start on `http://localhost:8001` (or the port specified in env-config.yaml)

### Run gRPC Server

```bash
python -m agent.entrypoint.grpc_server
```

## Testing

### Test HTTP Endpoint

```bash
# Non-streaming request
curl -X POST http://localhost:8001/agent/handle \
  -H "Content-Type: application/json" \
  -d @tests/test_http_request.json

# Streaming request
curl -X POST http://localhost:8001/agent/handle_stream \
  -H "Content-Type: application/json" \
  -d @tests/test_http_stream.json
```

### Run Tests

```bash
# Unit tests
pytest tests/unit/

# Integration tests
pytest tests/integration/

# E2E tests
pytest tests/e2e/
```

## Configuration

Main configuration files:
- `env-config.yaml`: General configuration
- `env-config.secret.yaml`: API keys and secrets (gitignored)
- `agent/config/llm_config.json`: LLM model configurations
- `agent/config/suggestions.py`: Contextual suggestions per sub-intent

## Vector Database Setup

For intent routing using semantic search:

```bash
# Seed vector database with intent samples
python scripts/seed_intent_samples.py
```

Set `ENABLE_VECTOR_DB_ROUTING=true` in env-config.yaml to enable.

## Project Structure

```
agent/
├── config/          # Configuration files
├── entrypoint/      # HTTP and gRPC servers
├── graph/           # LangGraph nodes and orchestration
├── handlers/        # Request handlers
├── intent_router/   # Intent classification
├── llm_service/     # LLM clients and services
├── models/          # Pydantic models
├── services/        # Vector DB and embedding services
└── utils/           # Utilities

scripts/             # Utility scripts
tests/              # Test suites
```

## Environment Variables

Key environment variables:
- `AGENT_NAME`: Agent identifier (default: "education")
- `HTTP_PORT`: HTTP server port (default: 8001)
- `GRPC_PORT`: gRPC server port (default: 50051)
- `AZURE_OPENAI_API_KEY`: Azure OpenAI API key
- `AZURE_OPENAI_ENDPOINT`: Azure OpenAI endpoint
- `ENABLE_VECTOR_DB_ROUTING`: Enable semantic intent routing
- `QDRANT_URL`: Qdrant vector database URL (if using)

See `env-config.yaml.example` for full list.

## License

MIT
