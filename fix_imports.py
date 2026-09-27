import glob
import os

files = glob.glob('backend/app/api/v1/endpoints/*.py')
for file in files:
    with open(file, 'r') as f:
        content = f.read()
    
    content = content.replace('from ...', 'from backend.app.')
    
    with open(file, 'w') as f:
        f.write(content)
        
print("Fixed imports")
