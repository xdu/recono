# Development Container Setup

This project includes a Dev Container configuration for a consistent development environment using Docker and VS Code Dev Containers.

## Prerequisites

- [Docker](https://www.docker.com/get-started) installed and running
- [Visual Studio Code](https://code.visualstudio.com/) with the [Dev Containers extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers)

## Quick Start

1. **Open in Dev Container**
   - Open this project in VS Code
   - Press `F1` or `Ctrl+Shift+P` (Cmd+Shift+P on macOS)
   - Select "Dev Containers: Reopen in Container"
   - VS Code will build the container and connect to it

   Or, if opening from a fresh clone:
   - Click the "Dev Container: Open Folder in Container" button when prompted
   - Or use the Command Palette: `Dev Containers: Open Folder in Container`

2. **Wait for Setup**
   - The container will be built automatically
   - Dependencies will be installed via `postCreateCommand`
   - This may take a few minutes on the first run

3. **Configure Environment Variables**
   - Copy `.env.example` to `.env`:
     ```bash
     cp .env.example .env
     ```
   - Edit `.env` and add your OpenRouter API key (optional, for text cleaning)

## What's Included

The Dev Container comes pre-configured with:

### System Dependencies
- **Python 3.11** - Runtime environment
- **Tesseract OCR** - For text extraction from images
- **Poppler utilities** - For PDF to image conversion
- **Ghostscript** - For PostScript/PDF processing
- **Git** - Version control

### Python Packages
All dependencies from `requirements.txt`:
- Flask 2.3.3
- pdf2image, pytesseract, Pillow (OCR and image processing)
- PyPDF2 (PDF manipulation)
- requests (API calls)
- python-dotenv (Environment variables)
- GitPython (Git integration)

### Development Tools
- **Black** - Code formatter
- **Pylint** - Code linter
- **Flake8** - Style checker
- **Mypy** - Type checker
- **Pytest** - Testing framework

### VS Code Extensions
The following extensions are automatically installed:
- Python (Microsoft)
- Pylance (Microsoft)
- Flask (Microsoft)
- Python Debugger (Microsoft)
- GitLens (GitKraken)
- Docker (Microsoft)
- Code Spell Checker (Street Side Software)

## Running the Application

Once inside the dev container:

### Option 1: Using VS Code Tasks (Recommended)

1. **Open the Command Palette** (`F1` or `Ctrl+Shift+P` / `Cmd+Shift+P`)
2. **Run "Tasks: Run Task"**
3. **Select one of the following options**:
   - **"Run Flask App"** - Runs the application with standard settings
   - **"Flask App (Debug Mode)"** - Runs with debug mode enabled for auto-reload

4. **Access the application**:
   - Open your browser to `http://localhost:5000`
   - The port is automatically forwarded by the dev container configuration

### Option 2: Using Terminal

1. **Start the Flask development server**:
   ```bash
   python app.py
   ```

2. **For development with auto-reload**:
   ```bash
   python -m flask run --host=0.0.0.0 --port=5000 --debug
   ```

3. **Access the application**:
   - Open your browser to `http://localhost:5000`

## Workspace Structure

- `/workspace` - Your project root directory
- All changes made in the container are reflected in your local filesystem
- The container mounts your project directory as a volume

## Troubleshooting

### Container won't start
- Ensure Docker is running: `docker ps`
- Check Docker disk space: `docker system df`
- Rebuild the container: `Dev Containers: Rebuild Container` from command palette

### Python dependencies not installing
- Check the `postCreateCommand` output in the dev container logs
- Manually install: `pip install -r requirements.txt`

### Tesseract not working
- Verify installation: `tesseract --version`
- Check language data: `tesseract --list-langs`

### Port 5000 already in use
- Stop any other Flask servers running locally
- Or change the port in `app.py` and update `forwardPorts` in `devcontainer.json`

### Performance Issues
- Increase Docker resources in Docker Desktop settings (Memory, CPU)
- Use `.dockerignore` to exclude unnecessary files from builds

## Customization

### Adding Extensions
Edit `.devcontainer/devcontainer.json` and add to the `extensions` array:
```json
"extensions": [
  "ms-python.python",
  "your.extension.name"
]
```

### Changing Python Version
Edit `.devcontainer/devcontainer.json`:
```json
"ghcr.io/devcontainers/features/python:1": {
  "version": "3.12"  // or your preferred version
}
```

### Adding System Dependencies
Edit `.devcontainer/Dockerfile`:
```dockerfile
RUN apt-get update && apt-get install -y \
    your-package-here \
    && rm -rf /var/lib/apt/lists/*
```

## Additional Resources

- [VS Code Dev Containers Documentation](https://code.visualstudio.com/docs/devcontainers/containers)
- [Dev Container Features](https://containers.dev/features)
- [Docker Documentation](https://docs.docker.com/)

## Support

If you encounter issues:
1. Check the Troubleshooting section above
2. Review the dev container logs in VS Code's "Output" panel (select "Dev Containers" from the dropdown)
3. Reopen the project in a new container if configuration changes were made