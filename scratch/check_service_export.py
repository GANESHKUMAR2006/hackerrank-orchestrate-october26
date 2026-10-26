import json

with open('dataset/evidence/records/service_resource_export_20260915_114455.json', encoding='utf-8') as f:
    exp_data = json.load(f)

# Let's inspect the exact ordering of lookups and profiles in service_resource_export_20260915_114455.json
lookups = exp_data['service_exports']['account_service']['profile_lookups']
profiles = exp_data['service_exports']['analytics_platform']['profiles']

print("Lookups in service_resource_export:")
for l in lookups:
    print(l)

print("\nProfiles in service_resource_export:")
for p in profiles:
    print(p)
