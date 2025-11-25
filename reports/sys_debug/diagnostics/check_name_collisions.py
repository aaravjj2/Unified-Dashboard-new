import os

collisions = []
# Adjust path to financial_dashboard/tabs
root_dir = 'financial_dashboard/tabs'

if os.path.exists(root_dir):
    for root, dirs, files in os.walk(root_dir):
        for f in files:
            name = os.path.splitext(f)[0]
            if os.path.isdir(os.path.join(root, name)):
                collisions.append(os.path.join(root, f))
    print("\n".join(collisions))
else:
    print(f"Directory {root_dir} not found")
