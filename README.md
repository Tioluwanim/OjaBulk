# OjaBulk

OjaBulk is a FastAPI + Next.js platform for pooled procurement, trader onboarding, OTP login, Nomba virtual accounts, reconciliation, payout automation, and USSD access for Nigerian market traders.

## What’s in the repo

- `main.py` starts the FastAPI app and mounts the backend routers.
- `frontend/` contains the Next.js marketing site, portal, and admin dashboard.
- `models/`, `routers/`, `services/`, and `engine/` contain the backend domain logic.
- `scripts/` contains maintenance utilities for demo data and virtual accounts.

## Setup

Backend:

```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

Frontend:

```bash
cd frontend
npm install
```

## Run

Backend:

```bash
uvicorn main:app --reload
```

Frontend:

```bash
cd frontend
npm run dev
```

## Demo login details

The demo login flow uses fixed OTP values so judges do not depend on live SMS delivery.

- Trader portal phone: `08099999001`
- Admin dashboard phone: `08099999002`
- OTP for both demo accounts: `000000`

These values are also used by the frontend landing page and backend OTP interception logic.

## Demo virtual account utilities

The demo trader account is the trader at `08099999001`.

Clear demo-only trader history while keeping the real virtual account details in place:

```bash
python scripts/remove_demo_virtual_account.py
```

Provision a real Nomba virtual account for the demo trader:

```bash
python scripts/provision_real_virtual_account.py
```

The provisioning script requires the Nomba environment variables already configured in `.env` or your deployment environment.

## Environment variables

At minimum, the backend expects these values:

- `DATABASE_URL`
- `NOMBA_ACCOUNT_ID`
- `NOMBA_SUB_ACCOUNT_ID`
- `NOMBA_CLIENT_ID`
- `NOMBA_CLIENT_SECRET`
- `NOMBA_WEBHOOK_SECRET`

Useful demo/auth values:

- `DEMO_PHONE_NUMBERS=08099999001,08099999002`
- `DEMO_OTP_CODE=000000`

## Notes

- The trader model keeps `virtual_account_number`, `bank_name`, and `bank_account_name` directly on the trader row.
- The cleanup script deletes demo trader payments, ledger entries, pool contributions, and esusu rows, then resets the cached balances on that trader.
- OTP login for demo accounts bypasses SMS delivery and uses the fixed demo code.
- The backend and frontend are meant to run together for the full demo flow.