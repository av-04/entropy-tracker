import subprocess
import os
import sys

# Move to demo-repo
demo_dir = os.path.join(os.getcwd(), "repos", "demo-repo")

os.environ["DATABASE_URL"] = "postgresql://postgres:entropy@localhost:5433/entropy"

# Checkout new branch
subprocess.run(["git", "checkout", "-b", "diff-test"], cwd=demo_dir, check=True)

# Modify a file
target_file = os.path.join(demo_dir, "auth", "tokens.py")
with open(target_file, "a") as f:
    f.write("\n# This is a dummy churn commit to test the diff\nprint('churn')\n")

# Commit
subprocess.run(["git", "add", "."], cwd=demo_dir, check=True)
subprocess.run(["git", "commit", "-m", "chore: add diff test churn"], cwd=demo_dir, check=True)

# Run entropy diff
print("Running entropy diff --base main...")
diff_cmd = [sys.executable, "-m", "entropy.cli", "diff", demo_dir, "--base", "main"]
result = subprocess.run(diff_cmd, cwd=os.getcwd(), capture_output=True, text=True)

print(result.stdout)
if result.stderr:
    print("STDERR:", result.stderr)

# Cleanup
subprocess.run(["git", "checkout", "main"], cwd=demo_dir, check=True)
subprocess.run(["git", "branch", "-D", "diff-test"], cwd=demo_dir, check=True)
