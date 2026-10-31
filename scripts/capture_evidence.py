"""Capture REAL running Django admin and passed-exam browser screens.

This script is intended for local development / GitHub Actions with demo data.
It does not fabricate or edit screenshots.
"""
from pathlib import Path
import time
from urllib.error import URLError
from urllib.request import urlopen

from playwright.sync_api import sync_playwright

BASE_URL = "http://127.0.0.1:8000"
OUT = Path("evidence")
OUT.mkdir(exist_ok=True)


def wait_for_server():
    for attempt in range(60):
        try:
            with urlopen(BASE_URL + "/admin/login/", timeout=2) as response:
                if response.status == 200:
                    return
        except (URLError, TimeoutError):
            pass
        time.sleep(1)
    raise RuntimeError("Django server did not start in time")


def main():
    wait_for_server()
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        admin = browser.new_page(viewport={"width": 1440, "height": 900}, device_scale_factor=1)
        admin.goto(BASE_URL + "/admin/login/?next=/admin/")
        admin.locator("#id_username").fill("demo_admin")
        admin.locator("#id_password").fill("admin12345")
        admin.get_by_role("button", name="Log in").click()
        admin.wait_for_url("**/admin/")
        assert admin.get_by_text("Authentication and Authorization").count() >= 1
        assert admin.get_by_text("Onlinecourse").count() >= 1
        admin.screenshot(path=str(OUT / "03-admin-site.png"), full_page=True)
        print("Saved 03-admin-site.png from the running Django admin.")

        student = browser.new_page(viewport={"width": 1440, "height": 900}, device_scale_factor=1)
        student.goto(BASE_URL + "/onlinecourse/login/")
        student.locator("#login-username").fill("demo_student")
        student.locator("#login-password").fill("student12345")
        student.get_by_role("button", name="Sign in").click()
        student.wait_for_url("**/onlinecourse/")
        student.get_by_role("link", name="Open course").first.click()
        student.get_by_label("Models", exact=True).check()
        student.get_by_label("SELECT", exact=True).check()
        student.get_by_label("Creating database records", exact=True).check()
        student.get_by_label("Filtering database records", exact=True).check()
        student.get_by_label("urls.py", exact=True).check()
        student.get_by_role("button", name="Submit exam").click()
        student.get_by_role("heading", name="Congratulations!").wait_for()
        score = student.locator(".score-pill").inner_text().strip()
        assert score == "100.0%", f"Unexpected exam grade: {score}"
        student.screenshot(path=str(OUT / "07-final.png"), full_page=True)
        print("Saved 07-final.png from a real completed exam with 100.0%.")
        browser.close()


if __name__ == "__main__":
    main()
