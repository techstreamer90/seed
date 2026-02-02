import re
import sys

input_file = sys.argv[1] if len(sys.argv) > 1 else r'C:\seed\old_prompts\26.01.30.md'
output_file = sys.argv[2] if len(sys.argv) > 2 else r'C:\seed\old_prompts\26.01.30_conversations.md'

with open(input_file, 'r', encoding='utf-8', errors='replace') as f:
    content = f.read()

lines = content.split('\n')
result = []
in_code_block = False

for line in lines:
    stripped = line.strip()

    # Track code blocks
    if '```' in stripped:
        in_code_block = not in_code_block
        continue
    if in_code_block:
        continue

    # Keep user prompts (>)
    if stripped.startswith('>'):
        result.append(line)
        continue

    # Skip empty lines (but track them)
    if not stripped:
        result.append('')
        continue

    # Skip if starts with special characters or numbers
    special_chars = '●✻⎿…│├└┌┐┘┬┴┼─+{}"[]0123456789'
    if stripped[0] in special_chars:
        continue

    # Skip lines that look like file paths
    if '\\' in stripped or stripped.startswith('/') or '::' in stripped:
        continue

    # Skip lines with line numbers embedded (like "   42  some text")
    if re.search(r'^\s*\d+\s+', line):
        continue

    # Skip git/tool output patterns
    skip_patterns = [
        r'^Changes (to be committed|not staged)',
        r'^(create|delete|modify) mode',
        r'^\s*(create|delete) mode',
        r'^Your branch',
        r'^nothing to commit',
        r'^drwxr',
        r'^-rw',
        r'^On branch',
        r'Interrupted',
        r'ctrl\+o',
        r'^VERIFIED',
        r'^DRIFTED',
        r'^expected:',
        r'^actual:',
        r'^\.\.\.',
        r'^spawnie/',
        r'^seed/',
        r'^BAM/',
        r'^\(use "git',
        r'^\s*\(use "git',
        r'\.py` detects',
        r'-rift\.',
    ]
    if any(re.search(p, stripped) for p in skip_patterns):
        continue

    # Only keep lines that look like natural prose (have some words)
    words = re.findall(r'[a-zA-Z]{3,}', stripped)
    if len(words) >= 2:  # At least 2 words with 3+ chars
        result.append(line)

# Clean up multiple blank lines
output = '\n'.join(result)
output = re.sub(r'\n{3,}', '\n\n', output)

with open(output_file, 'w', encoding='utf-8') as f:
    f.write(output)

print(f"Original: {len(content)} chars")
print(f"Condensed: {len(output)} chars")
print(f"Reduction: {100 - (len(output)*100//len(content))}%")
