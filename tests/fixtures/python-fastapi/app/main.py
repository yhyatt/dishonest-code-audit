# Synthetic fixture — intentionally contains stub patterns for the audit harness.

from fastapi import FastAPI

app = FastAPI()


@app.post("/charge")
def charge_endpoint(amount: int) -> dict:
    # HIGH: route raises NotImplementedError in a user-reachable endpoint.
    raise NotImplementedError("billing not implemented yet")


@app.get("/items")
def list_items() -> dict:
    # HIGH: route returns hardcoded placeholder content.
    return {"items": ["placeholder"], "todo": "wire to database"}
