# 3D Archaeological Analysis Tool

This repository contains the source code for a 3D archaeological analysis tool powered by an AI agent based on the Model Context Protocol. The frontend of the application is implemented using the Godot Game Engine and the backend, the AI assistant, is implemented using Python as a local backend using FastAPI. The LLM provider is currently set to use local models through Ollama.

## Structure of the Repository

### ai-agent
Source code for the Python backend of the AI assistant. You can use any tools to package or run the code, but it is recommended to use UV as a package manager and PyInstaller to package the program.

### user-client
Source code for the frontend, implemented using Godot 4.x. The code makes use of a GDExtension module, godot-ply, which is implemented in another repository. Libraries are included for simplicity.

### scripts
Build scripts for the project.

---

## Dependencies

For this project to work, you need the following installed:

* **Ollama** (configured to run local LLM models)
* **Godot** (version 4.x)
* **Python** (along with all the packages specified inside the `ai-agent` directory)
