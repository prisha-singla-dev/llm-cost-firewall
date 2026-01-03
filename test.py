from app.analyzer import analyzer

print("Simple:", analyzer.analyze("What is 2+2?"))
print(
    "Complex:",
    analyzer.analyze(
        "Analyze the philosophical implications of artificial consciousness"
    ),
)
