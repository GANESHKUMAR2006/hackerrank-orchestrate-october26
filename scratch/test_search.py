import glob

for f in ['dataset/evidence/databases/customer_data_inventory_20260213.sql', 'dataset/evidence/databases/customer_data_reporting_replica_20260208.sql']:
    with open(f, 'r', encoding='utf-8', errors='ignore') as fp:
        for line in fp:
            if '"user_50"' in line or '"user_48"' in line:
                print(f, line.strip()[:150])
