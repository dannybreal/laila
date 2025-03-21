#!/bin/bash

# Install dependencies
pip install -r requirements.txt

# Create patch directory
mkdir -p patch

# Create a patched version of asyncio/base_events.py
cat > patch/base_events_patch.py << 'EOL'
import re

# Path to asyncio/base_events.py
base_events_path = None

# Look for the file in site-packages
import site
for site_path in site.getsitepackages():
    potential_path = f"{site_path}/asyncio/base_events.py"
    try:
        with open(potential_path, 'r') as f:
            content = f.read()
            if 'async(' in content:
                base_events_path = potential_path
                break
    except:
        pass

# Apply the patch
if base_events_path:
    with open(base_events_path, 'r') as f:
        content = f.read()
    
    # Replace async( with ensure_future(
    patched_content = re.sub(r'tasks\.async\(', 'tasks.ensure_future(', content)
    
    with open(base_events_path, 'w') as f:
        f.write(patched_content)
    
    print(f"Successfully patched {base_events_path}")
else:
    print("Could not find asyncio/base_events.py")
EOL

# Execute the patch
python patch/base_events_patch.py

# Continue with normal build process
echo "Build completed" 