import sys
from modules.noise_analysis import analyze

path = sys.argv[1] if len(sys.argv) > 1 else "outputs/working_copy_test.jpg"
result = analyze(path)
for key, value in result.items():
    print(f"{key:20}: {value}")