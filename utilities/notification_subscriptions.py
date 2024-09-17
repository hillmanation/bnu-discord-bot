import json

# Path to the JSON file
subscriptions_file = 'assets/subscriptions/subscriptions.json'


# Load subscriptions from the file
def load_subscriptions():
    try:
        with open(subscriptions_file, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


# Save subscriptions to the file
def save_subscriptions(subscriptions):
    with open(subscriptions_file, 'w') as f:
        json.dump(subscriptions, f, indent=4)
