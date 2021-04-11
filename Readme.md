# Playing around with websockets

Is this how one scales websockets?
Multiple redis instances?

## Architecture

```
redis
+-(pubsub)- edge
    +-(websocket)- client
    +-(websocket)- client
    [...]
+-(pubsub)- edge
    +-(websocket)- client
    [...]
[...]
```

- Edges talk to redis with pub/sub
- Browsers talk to edges with wesockets
- When client sends a message it is published to redis
- When edge receives a message from redis it is broadcasted to all connected clients