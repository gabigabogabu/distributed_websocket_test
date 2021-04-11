from typing import List

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

from pydantic import BaseSettings

import websockets
import asyncio
import aioredis

class Settings(BaseSettings):
	backend_uri: str = 'ws://localhost:8000'
	redis_uri: str = 'redis://localhost:6379'

class SocketManager:
	def __init__(self):
		self.sockets: List[WebSocket] = []

	async def connect(self, ws: WebSocket):
		await ws.accept()
		self.sockets.append(ws)

	def disconnect(self, ws: WebSocket):
		self.sockets.remove(ws)

	async def send(self, ws: WebSocket, msg: str):
		await ws.send_text(msg)

	async def broadcast(self, ws: WebSocket, msg: str):
		for s in self.sockets:
			if s is not ws:
				await s.send_text(msg)

settings = Settings()
app = FastAPI()
redis = None
socket_manager = SocketManager()

@app.on_event('startup')
async def init_redis():
	global redis
	redis = await aioredis.create_redis_pool(settings.redis_uri)
	messages, = await redis.subscribe('messages')
	async def reader(channel: aioredis.Channel):
		async for msg in channel.iter():
			print(f'msg: {msg.decode()}')
			await socket_manager.broadcast(None, msg.decode())

	asyncio.get_running_loop().create_task(reader(messages))


@app.get("/")
async def get():
	return HTMLResponse("""
<!DOCTYPE html>
<html>
	<head>
		<title>Chat</title>
	</head>
	<body>
		<h1>WebSocket Chat</h1>
		<h2>Your ID: <span id="ws-id"></span></h2>
		<form action="" onsubmit="sendMessage(event)">
			<input type="text" id="messageText" autocomplete="off"/>
			<button>Send</button>
		</form>
		<ul id='messages'>
		</ul>
		<script>
			var client_id = Date.now()
			document.querySelector("#ws-id").textContent = client_id;
			var ws = new WebSocket(`ws://localhost:8001/ws/${client_id}`);
			ws.onmessage = function(event) {
				var messages = document.getElementById('messages')
				var message = document.createElement('li')
				var content = document.createTextNode(event.data)
				message.appendChild(content)
				messages.appendChild(message)
			};
			function sendMessage(event) {
				var input = document.getElementById("messageText")
				ws.send(input.value)
				input.value = ''
				event.preventDefault()
			}
		</script>
	</body>
</html>
""".replace('ws://localhost:8001', settings.backend_uri))

@app.websocket("/ws/{client_id}")
async def ws(ws: WebSocket, client_id: int):
	await socket_manager.connect(ws)
	await redis.publish('messages', f"Client #{client_id} joined the chat")
	try:
		while True:
			data = await ws.receive_text()
			await socket_manager.send(ws, f"You wrote: {data}")
			await redis.publish('messages', f"Client #{client_id} says: {data}")
	except WebSocketDisconnect:
		await socket_manager.broadcast(ws, f"Client #{client_id} left the chat")
		socket_manager.disconnect(ws)
