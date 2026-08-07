import re

with open('frontend/admin/super-admin.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

stack = []

for line_num, line in enumerate(lines, 1):
    # Find all div openings and closings in order on this line
    tokens = re.findall(r'(<div\b[^>]*>|</div>)', line, re.I)
    for token in tokens:
        if token.lower().startswith('<div'):
            stack.append((line_num, token))
        elif token.lower() == '</div>':
            if stack:
                stack.pop()
            else:
                print(f"Extra closing </div> at line {line_num}")

print(f"\nRemaining unclosed divs in stack: {len(stack)}")
for line_num, token in stack[-10:]:
    print(f"  Line {line_num}: {token[:60]}")
