"""
LLM Callback Utilities - Helper functions for parsing and formatting LLM logs.

Ported from old_code for agent/ structure.
"""
import re
import ast
import json
import uuid


ROLE_TOKENS = {
    'System': 'system',
    'Human': 'user',
    'AI': 'assistant',
    'Assistant': 'assistant',
    'Tool': 'tool'
}


def try_parse_literal(s: str):
    """Try to parse string as Python literal or JSON."""
    s = s.strip()
    try:
        return ast.literal_eval(s)
    except Exception:
        try:
            return json.loads(s)
        except Exception:
            return None


def extract_query_from_tool_text(text: str):
    """Extract query from tool text using regex patterns."""
    m = re.search(r'Người dùng hỏi:\s*["\']([^"\']+)["\']', text)
    if m:
        return m.group(1).strip()
    m2 = re.search(r"truy vấn\s+'([^']+)'", text)
    if m2:
        return m2.group(1).strip()
    return None


def parse_log_to_blocks(log_text: str):
    """Parse log text into role-based blocks."""
    blocks = []
    current_role = None
    current_lines = []
    token_re = re.compile(r'^(System|Human|AI|Assistant|Tool):\s*(.*)$')
    for raw in log_text.splitlines():
        line = raw.rstrip('\n')
        m = token_re.match(line)
        if m:
            if current_role is not None:
                blocks.append({'role_token': current_role, 'text': "\n".join(current_lines)})
            current_role = m.group(1)
            rest = m.group(2)
            current_lines = []
            if rest:
                current_lines.append(rest)
        else:
            if current_role is not None:
                current_lines.append(line)
            else:
                if blocks:
                    blocks[-1]['text'] += '\n' + line
    if current_role is not None:
        blocks.append({'role_token': current_role, 'text': "\n".join(current_lines)})
    return blocks


def build_messages_from_blocks(blocks):
    """Build OpenAI-format messages from parsed blocks."""
    messages = []
    i = 0
    while i < len(blocks):
        b = blocks[i]
        role_token = b['role_token']
        role = ROLE_TOKENS.get(role_token, role_token.lower())
        text = b['text'].strip()

        # AI followed by Tool -> represent as assistant message with tool_calls
        if role_token in ('AI', 'Assistant') and i + 1 < len(blocks) and blocks[i + 1]['role_token'] == 'Tool':
            tool_block = blocks[i + 1]
            tool_text = tool_block['text'].strip()
            call_id = f"call_{uuid.uuid4().hex}"
            func_name = 'tool'  # default
            extracted_query = extract_query_from_tool_text(tool_text)
            args_obj = {'raw_output': tool_text}
            if extracted_query:
                args_obj['query'] = extracted_query
            func_obj = {'name': func_name, 'arguments': json.dumps(args_obj, ensure_ascii=False)}
            tool_call = {'id': call_id, 'type': 'function', 'function': func_obj}
            messages.append({'role': 'assistant', 'content': None, 'tool_calls': [tool_call]})
            i += 2
            continue

        # normal block: try to parse list-of-dicts
        content = text
        if content.startswith('[') and content.endswith(']'):
            parsed = try_parse_literal(content)
            if isinstance(parsed, list) and all(isinstance(x, dict) for x in parsed):
                content = parsed
        messages.append({'role': role, 'content': content})
        i += 1
    return messages
