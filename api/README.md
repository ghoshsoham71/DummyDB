# FastAPI Project

A simple FastAPI project setup with modern Python tooling using `uv` package manager.

## Project Structure

```
├── .env
├── .gitignore
├── pyproject.toml
├── uv.lock
├── main.py
└── src/
    ├── app.py
    ├── config.py
    ├── routers/
    ├── utils/
    └── lib/
```

## Prerequisites

- Python 3.8+
- [uv](https://github.com/astral-sh/uv) package manager

## Installation

1. Clone the repository
2. Install dependencies:
   ```bash
   uv sync
   ```

## Running the Application

Start the development server:
```bash
uv run uvicorn main:app --reload
```

The API will be available at `http://localhost:8000`

## API Documentation

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Development

### Adding Dependencies

```bash
uv add package-name
```

### Adding Development Dependencies

```bash
uv add --dev package-name
```

### Environment Variables

Copy `.env.example` to `.env` and update the values as needed.

## License

MIT