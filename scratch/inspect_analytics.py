import json

with open('dataset/evidence/records/customer_data_snapshot_bundle_20260917.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

def find_item(obj, path=''):
    if isinstance(obj, dict):
        rid = obj.get('resource_id')
        if rid in ['analytics_1895', 'analytics_4566']:
            print(f'Found at {path}: {rid}')
            print(json.dumps(obj, indent=2))
        for k, v in obj.items():
            find_item(v, f'{path}.{k}')
    elif isinstance(obj, list):
        for idx, item in enumerate(obj):
            find_item(item, f'{path}[{idx}]')

find_item(data)
