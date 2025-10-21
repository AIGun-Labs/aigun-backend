import asyncio
import websockets
import json
from datetime import datetime


async def websocket_client():
    uri = "ws://localhost:10106/ws/v1/subscription"

    async with websockets.connect(uri, ping_interval=None) as websocket:  # Disable automatic ping
        init_msg = {
            "type": "init",
            "data": {
                "authorization": "Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZDQ2MTkyYi1lODNkLTQwODctOTZjZS01OTUyNTk4ZjM3Y2QiLCJpc3MiOiJ1c2VyX3NlcnZpY2UiLCJleHAiOjE3NDMwODE0NjcsImlhdCI6MTc0MDQ4OTQ2N30.w2EC-XhhPInPiIoW79tadO5_51O_Umv-DLSMqAevTBh5N2KA5PtO55Vh7KK92tHeGLizPjuExO2PLMjkJPvZ1-FpGE3huSM6X9mDfr7eC-FJWz0nnkWjzreLfXszHoPX78YCsAJX8_ToKXwaQiCDElifxPtd4COSIgCSg1g6M6zbQRrJ5bb58rLOW2Cnjd5-W26vS72Uvy0XuKYg0GCjzRcMaatC0RUVfUhtjTj2sRPnXc6X6GQ-cVuUL3YYmfxhUKBLHXPgheTjQU8uRweR0gqiI5qpyzmIHt2DiPdMcUKRM9gq2y-YZlDQBVRh__lXe3Zqivw0zBOgW-VOOgczag",
                # Replace with actual token
                "subscriptions": "3ac43583-8898-4924-95e1-872d480621f2#0265790b-d9d2-4113-be68-069595e4c22d#a57a8150-e7a9-4737-aa7b-5091c7e937e2"
                # Replace with actual subscription group
            }
        }
        # Must wait for server response after sending initialization message
        await websocket.send(json.dumps(init_msg))
        try:
            # Add response waiting (server will send welcome message first)
            welcome = await asyncio.wait_for(websocket.recv(), timeout=5)
            print("Server response:", welcome)
        except asyncio.TimeoutError:
            print("Server did not respond to init message")
            return

        # Modify heartbeat sending method (match server protocol)
        async def send_ping():
            while True:
                await asyncio.sleep(5)
                # Use ping format expected by server
                await websocket.send(json.dumps({"type": "ping"}))

                # Create message receiving task

        async def receive_messages():
            while True:
                try:
                    message = await websocket.recv()
                    print(f"[{datetime.now().isoformat()}] Received: {message}")
                except websockets.exceptions.ConnectionClosed:
                    break

        # Create heartbeat sending task
        async def send_ping():
            while True:
                await asyncio.sleep(5)  # 5 second interval
                ping_msg = {
                    "type": "ping",
                    "data": {"timestamp": datetime.now().isoformat()}
                }
                await websocket.send(json.dumps(ping_msg))
                print(f"[{datetime.now().isoformat()}] Sent ping")

        # Run receiving and heartbeat tasks simultaneously
        await asyncio.gather(
            receive_messages(),
            send_ping()
        )


if __name__ == "__main__":
    try:
        asyncio.run(websocket_client())
    except KeyboardInterrupt:
        print("\nConnection closed by user")