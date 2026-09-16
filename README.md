# Asistente IA para Análisis 3D en Patrimonio Cultural

Este repositorio contiene el código fuente de la aplicación desarrollada para mi Trabajo Fin de Máster: una herramienta de asistencia en análisis 3D orientado al patrimonio cultural.
El asistente está basado en LLMs (***Large Language Models***) que emplean un servidor MCP (***Model Context Protocol***) de herramientas de procesamiento y análisis geométrico para asistir en las tareas.
La aplicación cuenta con una interfaz de usuario que permite visualizar e interactuar con los modelos 3D y conversar con el asistente.

![application](docs/images/application.png)

## Estructura del Proyecto

El proyecto se estructura en dos bloques principales: un frontend, que actúa como la interfaz de usuario y aplicación cliente, y un backend que implementa el agente IA y el cliente-servidor MCP.
El directorio **ai-agent** implementa el backend empleando Python, FastAPI, Open3D y FastMCP. El directorio **user-client** implenta el frontend empleado Godot. Los scripts de automatización
para el proyecto pueden encontrarse en el directorio **scripts**.

![system architecture](docs/images/system-architecture.svg)

## Dependencias

Para hacer funcionar el proyecto a partir del código fuente es necesario contar con:

* **Python**: Todas las dependencias incluidas en proyecto python descrito en **ai-agent**.
* **Godot 4.x**: Para el cliente.

Además, es necesario disponer de un proveedor de servicios LLM. El proyecto puede funcionar mediante **Ollama** de forma local, empleando los puertos por defecto,
o mediante un proveedor remoto compatible con el estándar de la API de **OpenAI**.

---

# AI Assistant for 3D Analysis in Cultural Heritage

This repository contains the source code for the application developed as part of my Master's Thesis: an assistance tool for 3D analysis focused on cultural heritage.

The assistant is based on LLMs (***Large Language Models***) that use an MCP (***Model Context Protocol***) server providing geometric processing and analysis tools to assist with these tasks.

The application features a user interface that allows users to visualize and interact with 3D models and communicate with the assistant.

![application](docs/images/application.png)

## Project Structure

The project is divided into two main components: a frontend, which serves as the user interface and client application, and a backend, which implements the AI agent and the MCP client-server.

The **ai-agent** directory contains the backend, implemented using Python, FastAPI, Open3D, and FastMCP. The **user-client** directory contains the frontend, implemented using Godot. The project's automation scripts can be found in the **scripts** directory.

![system architecture](docs/images/system-architecture.svg)

## Dependencies

To run the project from the source code, the following are required:

* **Python**: All dependencies listed in the Python project described in **ai-agent**.
* **Godot 4.x**: For the client.

In addition, an LLM service provider is required. The project can run locally using **Ollama**, using its default ports, or through a remote provider compatible with the **OpenAI API** standard.
