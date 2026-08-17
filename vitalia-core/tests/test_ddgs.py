from ddgs import DDGS
ddgs = DDGS()
results = ddgs.text("python programming", max_results=3)
print("Type of results:", type(results))
try:
    results_list = list(results)
    print("Items:", len(results_list))
    if len(results_list) > 0:
        print("First item keys:", results_list[0].keys())
except Exception as e:
    print("Error:", e)
