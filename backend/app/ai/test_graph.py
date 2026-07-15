from app.ai.graph import graph

response = graph.invoke({
    "messages": [
        {
            "role": "user",
            "content": "Hello"
        }
    ]
})

print(response)