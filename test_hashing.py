from modules.hashing import analyze

result = analyze("samples/test.jpg")
for key, value in result.items():
    print(f"{key:15}: {value}")