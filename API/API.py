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