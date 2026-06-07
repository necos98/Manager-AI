"""Test MCP connection with proper session handling via http.client."""
import http.client
import json

HOST = "127.0.0.1"
PORT = 8000

def mcp_call(conn, method, params=None, session_id=None):
    """Make an MCP call via StreamableHTTP."""
    body = json.dumps({
        "jsonrpc": "2.0",
        "id": 1,
        "method": method,
        **({"params": params} if params else {})
    })
    
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "Content-Length": str(len(body)),
    }
    if session_id:
        headers["Mcp-Session-Id"] = session_id
    
    conn.request("POST", "/mcp/", body=body, headers=headers)
    resp = conn.getresponse()
    body_data = resp.read().decode()
    
    new_session_id = resp.getheader("Mcp-Session-Id")
    
    # Parse SSE or JSON
    events = []
    for line in body_data.split("\n"):
        if line.startswith("data: "):
            events.append(json.loads(line[6:]))
    
    if events:
        return events[-1], new_session_id
    try:
        return json.loads(body_data), new_session_id
    except json.JSONDecodeError:
        return {"raw": body_data}, new_session_id

# Create persistent connection
conn = http.client.HTTPConnection(HOST, PORT, timeout=10)

try:
    # Step 1: Initialize
    print("=== 1. Initialize ===")
    result, session_id = mcp_call(conn, "initialize", {
        "protocolVersion": "2024-11-05",
        "capabilities": {},
        "clientInfo": {"name": "hermes-test", "version": "1.0"}
    })
    print(f"Result: {json.dumps(result, indent=2, ensure_ascii=False)}")
    print(f"Session ID: {session_id}")
    
    if not session_id:
        if "error" in result:
            print(f"\nERROR: {result['error']}")
        else:
            print("\nNo session ID received - aborting")
        exit(1)
    
    # Step 2: Tools/List to see what's available
    print("\n=== 2. Tools/List ===")
    result, _ = mcp_call(conn, "tools/list", session_id=session_id)
    if "error" in result:
        print(f"Error: {result['error']}")
    else:
        tools = result.get("result", {}).get("tools", [])
        print(f"Tools available: {len(tools)}")
        for t in tools:
            print(f"  - {t['name']}: {t.get('description', '')[:80]}")
    
    # Step 3: Get next issue
    print("\n=== 3. Get Next Issue ===")
    result, _ = mcp_call(conn, "tools/call", {
        "name": "get_next_issue",
        "arguments": {"project_id": "1baae1c7-22f1-4091-abec-b49da70cf46c"}
    }, session_id=session_id)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    
    # Step 4: Get issue details for the New one
    print("\n=== 4. Get Issue Details (57b65c6c) ===")
    result, _ = mcp_call(conn, "tools/call", {
        "name": "get_issue_details",
        "arguments": {
            "project_id": "1baae1c7-22f1-4091-abec-b49da70cf46c",
            "issue_id": "57b65c6c-5eb0-49d0-9191-c7a022a28641"
        }
    }, session_id=session_id)
    issue = result.get("result", result)
    print(json.dumps(issue, indent=2, ensure_ascii=False))

finally:
    conn.close()
