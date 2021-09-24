import json
import os

def save_json(file, order):
    with open(file, 'w') as f:
        json.dump(order, f, indent=4)

def load_json(file):
    with open(file, "r+") as f:
        return json.load(f)

def update_json(file, update):
    if os.path.exists(file):
        existing_file = load_json(file)
        existing_file.append(update)
    else: 
        existing_file = [update]
    save_json(file, existing_file)