import os
import subprocess
from datetime import datetime
import shutil

REPO_PATH = "repos/demo-repo"

def run_git(cmd, env=None):
    full_env = os.environ.copy()
    if env:
        full_env.update(env)
    subprocess.run(
        cmd, cwd=REPO_PATH, shell=True, check=True, env=full_env,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )

def main():
    if os.path.exists(REPO_PATH):
        subprocess.run(f"rmdir /s /q {os.path.abspath(REPO_PATH)}", shell=True)
    
    os.makedirs(REPO_PATH, exist_ok=True)
    run_git("git init")
    run_git("git checkout -b main")

    # 1. Setup the outdated requirements.txt
    with open(os.path.join(REPO_PATH, "requirements.txt"), "w") as f:
        f.write("requests==2.22.0\n")
        f.write("django==2.2.0\n")
        f.write("celery==4.3.0\n")
        f.write("cryptography==2.8\n")
    
    # Commit the requirements 35 months ago
    run_git("git add requirements.txt")
    run_git(
        'git commit -m "chore: initial dependencies"',
        env={
            "GIT_AUTHOR_DATE": "2023-05-01T10:00:00",
            "GIT_COMMITTER_DATE": "2023-05-01T10:00:00",
            "GIT_AUTHOR_NAME": "System",
            "GIT_AUTHOR_EMAIL": "system@company.com"
        }
    )

    # 2. auth/tokens.py: Knowledge 100% (Solo author left 2 years ago)
    os.makedirs(os.path.join(REPO_PATH, "auth"), exist_ok=True)
    with open(os.path.join(REPO_PATH, "auth", "__init__.py"), "w") as f: f.write("")
    with open(os.path.join(REPO_PATH, "auth", "tokens.py"), "w") as f:
        f.write("import cryptography\n")
        f.write("def generate_token(): return 'secret'\n")

    run_git("git add auth/")
    run_git(
        'git commit -m "feat: implement legacy tokens mechanism"',
        env={
            "GIT_AUTHOR_DATE": "2023-06-15T10:00:00",
            "GIT_COMMITTER_DATE": "2023-06-15T10:00:00",
            "GIT_AUTHOR_NAME": "Departed Dev",
            "GIT_AUTHOR_EMAIL": "departed@company.com"
        }
    )

    # 3. core/connector.py: Bus factor 1 (Single active author)
    os.makedirs(os.path.join(REPO_PATH, "core"), exist_ok=True)
    with open(os.path.join(REPO_PATH, "core", "__init__.py"), "w") as f: f.write("")
    with open(os.path.join(REPO_PATH, "core", "connector.py"), "w") as f:
        f.write("import requests\n")
        f.write("def connect():\n    pass\n")

    run_git("git add core/")
    run_git(
        'git commit -m "feat: core db connector"',
        env={
            "GIT_AUTHOR_DATE": "2026-01-01T10:00:00", # Recent commit so they are active
            "GIT_COMMITTER_DATE": "2026-01-01T10:00:00",
            "GIT_AUTHOR_NAME": "Active Survivor",
            "GIT_AUTHOR_EMAIL": "active@current.com"
        }
    )

    # 4. payments/gateway.py: High churn, no refactors, blast radius 12.
    os.makedirs(os.path.join(REPO_PATH, "payments"), exist_ok=True)
    with open(os.path.join(REPO_PATH, "payments", "__init__.py"), "w") as f: f.write("")
    
    # Setup initial gateway
    with open(os.path.join(REPO_PATH, "payments", "gateway.py"), "w") as f:
        f.write("import requests\nimport celery\nfrom auth.tokens import generate_token\nfrom core.connector import connect\n")
        f.write("def process_payment():\n    pass\n")
    
    run_git("git add payments/")
    run_git(
        'git commit -m "feat: initial payment gateway"',
        env={
            "GIT_AUTHOR_DATE": "2023-05-01T10:00:00",
            "GIT_COMMITTER_DATE": "2023-05-01T10:00:00",
            "GIT_AUTHOR_NAME": "Alice Founder",
            "GIT_AUTHOR_EMAIL": "alice@company.com"
        }
    )

    # Create 40 churn commits by random departed authors to age the file and increase churn ratio
    for i in range(1, 41):
        year = 2024 if i < 20 else 2025
        month = str((i % 12) + 1).zfill(2)
        with open(os.path.join(REPO_PATH, "payments", "gateway.py"), "a") as f:
            f.write(f"\n# Patch {i} for critical bug\n")
            for j in range(60):
                f.write(f"def patch_{i}_sub_{j}(): pass\n")
        
        run_git("git add payments/gateway.py")
        run_git(
            f'git commit -m "fix: emergency patch {i}"',
            env={
                "GIT_AUTHOR_DATE": f"{year}-{month}-15T10:00:00",
                "GIT_COMMITTER_DATE": f"{year}-{month}-15T10:00:00",
                "GIT_AUTHOR_NAME": f"Contractor {i}",
                "GIT_AUTHOR_EMAIL": f"contractor{i}@agency.com"
            }
        )
    
    # 5. Build blast radius for payments/gateway.py by creating 12 files that import it
    os.makedirs(os.path.join(REPO_PATH, "services"), exist_ok=True)
    with open(os.path.join(REPO_PATH, "services", "__init__.py"), "w") as f: f.write("")
    run_git("git add services/__init__.py")
    
    for i in range(12):
        with open(os.path.join(REPO_PATH, "services", f"service_{i}.py"), "w") as f:
            f.write("from payments.gateway import process_payment\ndef run_service():\n    process_payment()\n")
        run_git(f"git add services/service_{i}.py")
        run_git(
            f'git commit -m "feat: add service {i}"',
            env={
                "GIT_AUTHOR_DATE": "2024-01-01T10:00:00",
                "GIT_COMMITTER_DATE": "2024-01-01T10:00:00",
                "GIT_AUTHOR_NAME": "Alice Founder",
                "GIT_AUTHOR_EMAIL": "alice@company.com"
            }
        )

    print("✅ Demo repository generated successfully at ./repos/demo-repo")

if __name__ == "__main__":
    main()
