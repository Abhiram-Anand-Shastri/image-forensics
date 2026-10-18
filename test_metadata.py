from modules.metadata import analyze

result = analyze("outputs/working_copy_test.jpg")
for key, value in result.items():
    print(f"{key:20}: {value}")