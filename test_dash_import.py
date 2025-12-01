import sys
print(f"sys.path: {sys.path}")
import time
start = time.time()
print("Importing dash...")
import dash
print(f"Imported dash in {time.time() - start:.4f}s")
from dash import dcc, html
print("Imported dcc, html")
print("Success")
