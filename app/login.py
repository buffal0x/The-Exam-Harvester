from __future__ import annotations

import os
from pathlib import Path

import yaml
from playwright.sync_api import sync_playwright


def load_config() -> dict:
    with open("config/site.yaml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def run_login() -> None:
    config = load_config()

    site = config["site"]
    auth = config["auth"]
    selectors = config["selectors"]

    username_env = auth["username_env"]
    password_env = auth["password_env"]
    state_file = Path(auth["state_file"])

    username = os.getenv(username_env)
    password = os.getenv(password_env)

    if not username or not password:
        raise RuntimeError(
            f"Missing environment variables. Required: {username_env} and {password_env}"
        )

    state_file.parent.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        page.goto(site["login_url"], wait_until="domcontentloaded")
        page.wait_for_timeout(3000)

        inputs = page.locator(selectors["inputs"])
        input_count = inputs.count()

        if input_count < 2:
            raise RuntimeError(f"Expected at least 2 login inputs, found {input_count}")

        visible_inputs = []
        for i in range(input_count):
            candidate = inputs.nth(i)
            if candidate.is_visible():
                visible_inputs.append(candidate)

        if len(visible_inputs) < 2:
            raise RuntimeError(
                f"Expected at least 2 visible login inputs, found {len(visible_inputs)}"
            )

        visible_inputs[0].fill(username)
        visible_inputs[1].fill(password)

        submit_buttons = page.locator(selectors["submit"])
        submit_count = submit_buttons.count()

        clicked = False
        for i in range(submit_count):
            button = submit_buttons.nth(i)
            if button.is_visible():
                button.click()
                clicked = True
                break

        if not clicked:
            raise RuntimeError("Could not find a visible login submit button")

        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(5000)

        success_selector = selectors.get("login_success")
        if success_selector:
            page.locator(success_selector).first.wait_for(timeout=15000)

        context.storage_state(path=str(state_file))
        browser.close()

    print(f"Saved auth state to: {state_file}")