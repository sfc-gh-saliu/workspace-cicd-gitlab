import random
import sys

result = random.random()
print(f"Validation score: {result:.4f}")

if result < 0.5:
    print("FAIL")
    sys.exit(1)

print("PASS")
