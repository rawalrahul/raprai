"""A tiny ACP agent for tests: echoes the prompt, asks permission for a 'delete' request."""
import json
import sys

sid = "sess-1"


def send(msg):
    sys.stdout.write(json.dumps(msg) + "\n")
    sys.stdout.flush()


for line in sys.stdin:
    msg = json.loads(line)
    method, rid = msg.get("method"), msg.get("id")
    if method == "initialize":
        send({"jsonrpc": "2.0", "id": rid, "result": {"protocolVersion": 1, "agentInfo": {"name": "mock"}}})
    elif method == "session/new":
        send({"jsonrpc": "2.0", "id": rid, "result": {"sessionId": sid}})
    elif method == "session/prompt":
        text = msg["params"]["prompt"][0]["text"]
        if "delete" in text:
            send({"jsonrpc": "2.0", "id": 900, "method": "session/request_permission",
                  "params": {"sessionId": sid, "toolCall": {"title": "delete files"},
                             "options": [{"optionId": "allow", "name": "Allow", "kind": "allow_once"},
                                         {"optionId": "reject", "name": "Reject", "kind": "reject_once"}]}})
            # wait for the client's answer
            answer = json.loads(sys.stdin.readline())
            outcome = answer["result"]["outcome"]
            reply = "deleted" if outcome.get("optionId") == "allow" else "not allowed"
        else:
            reply = f"you said: {text}"
        send({"jsonrpc": "2.0", "method": "session/update",
              "params": {"sessionId": sid, "update": {"sessionUpdate": "agent_message_chunk",
                                                      "content": {"type": "text", "text": reply}}}})
        send({"jsonrpc": "2.0", "id": rid, "result": {"stopReason": "end_turn"}})
