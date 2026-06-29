import csv

with open('data/benchmark_results/pairwise_20260608_161926.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    count = 0
    print("=== Why did Multi lose EVEN AFTER prompt correction? ===")
    for row in reader:
        if row['metric'] == 'Specialization Depth' and row['winner'] == 'Single':
            print("Category:", row['category'])
            print("Query:", row['query'])
            print("Reason:", row['reason'])
            print("-" * 80)
            count += 1
            if count >= 5:
                break
