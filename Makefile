# Wundio – Developer Makefile
# Use on your dev machine (not on Pi) for faster iteration.

.PHONY: install run test lint clean web web-dev

VENV=.venv
PY=$(VENV)/bin/python
PIP=$(VENV)/bin/pip

# ── Setup ─────────────────────────────────────────────────────────────────────
install:
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip -q
	$(PIP) install -r core/requirements.txt
	$(PIP) install pytest httpx ruff -q
	@echo "✓ Dev environment ready. Run: make run"

# ── Core API ──────────────────────────────────────────────────────────────────
run:
	cd core && PYTHONPATH=. ../$(VENV)/bin/uvicorn main:app --reload --port 8000

# ── Tests ─────────────────────────────────────────────────────────────────────
test:
	PYTHONPATH=core $(VENV)/bin/pytest tests/ -v

# ── Lint ──────────────────────────────────────────────────────────────────────
lint:
	$(VENV)/bin/ruff check core/

# ── Web UI (React) ────────────────────────────────────────────────────────────
web-install:
	cd web && npm install

web-dev:
	cd web && npm run dev

web-build:
	cd web && npm run build
	@echo "✓ Web built → web/dist/ (served by FastAPI)"

# ── Website (Next.js / Vercel) ────────────────────────────────────────────────
website-install:
	cd website && npm install

website-dev:
	cd website && npm run dev

# ── Mock RFID scan (requires running API) ────────────────────────────────────
rfid-mock:
	@read -p "RFID UID to mock (hex, e.g. A1B2C3D4): " uid; \
	curl -s -X POST "http://localhost:8000/api/rfid/mock-scan/$$uid" | python3 -m json.tool

# ── Cleanup ───────────────────────────────────────────────────────────────────
clean:
	rm -rf $(VENV) web/dist web/node_modules website/.next website/node_modules
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
