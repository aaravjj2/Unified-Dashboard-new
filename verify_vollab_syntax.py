import ast
import sys

def check_syntax(file_path):
    try:
        with open(file_path, 'r') as f:
            source = f.read()
        ast.parse(source)
        print(f"Syntax OK: {file_path}")
        return True
    except SyntaxError as e:
        print(f"Syntax Error in {file_path}: {e}")
        return False

if __name__ == "__main__":
    files = [
        "/home/aarav/unified-dashboard/financial_dashboard/tabs/home.py",
        "/home/aarav/unified-dashboard/financial_dashboard/tabs/volatility_lab/layout.py",
        "/home/aarav/unified-dashboard/financial_dashboard/tabs/volatility_lab/callbacks.py"
    ]
    
    success = True
    for f in files:
        if not check_syntax(f):
            success = False
            
    sys.exit(0 if success else 1)
