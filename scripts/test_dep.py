from entropy.analyzers.dep_analyzer import DepAnalyzer

d = DepAnalyzer('./repos/click-full')
result = d.analyze()
for k, v in result.items():
    print(f"{k}: {v}")
