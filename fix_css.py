import os

template_dir = r"d:\FocusPulse\templates"
files = [f for f in os.listdir(template_dir) if f.endswith(".html")]

target = """    <link rel="stylesheet" href="{{ url_for('static', filename='css/modern.css') }}">
    <link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}">"""

replacement = """    <link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}">
    <link rel="stylesheet" href="{{ url_for('static', filename='css/modern.css') }}">"""

for file in files:
    path = os.path.join(template_dir, file)
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if target in content:
        content = content.replace(target, replacement)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Updated {file}")
