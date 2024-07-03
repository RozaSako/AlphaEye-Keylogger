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