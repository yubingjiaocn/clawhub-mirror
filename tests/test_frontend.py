"""
Playwright end-to-end tests for ClawHub Enterprise frontend.
Tests run against the real deployed CloudFront + API environment.

Covers: page rendering, navigation, login/logout flow, skill browsing,
search, admin panel, settings/API key management.
"""

import os
import re

import pytest
from playwright.sync_api import Page, expect

BASE_URL = os.environ.get(
    "CLAWHUB_FRONTEND_URL", "https://d1gta4s2b4m2k6.cloudfront.net"
)
ADMIN_USER = os.environ.get("CLAWHUB_ADMIN_USER", "admin")
ADMIN_PASS = os.environ.get("CLAWHUB_ADMIN_PASS", "admin123")


@pytest.fixture(scope="session")
def browser_context_args():
    return {"ignore_https_errors": True}


def login(page: Page, username: str = ADMIN_USER, password: str = ADMIN_PASS):
    """Helper: click Sign in, fill the modal, submit."""
    page.get_by_role("button", name="Sign in").first.click()
    page.get_by_label("Username").fill(username)
    page.get_by_label("Password").fill(password)
    # Click the submit button inside the login form
    page.locator("form").get_by_role("button", name="Sign in").click()
    # Wait for user menu to appear (indicates successful login)
    page.locator(".user-trigger").wait_for(timeout=10000)


# ── 1. Page Rendering ───────────────────────────────────────────────
class TestPageRendering:
    def test_home_page_loads(self, page: Page):
        page.goto(BASE_URL)
        expect(page).to_have_title(re.compile(r"ClawHub", re.IGNORECASE))
        expect(page.locator(".brand-name")).to_be_visible()

    def test_home_has_navigation(self, page: Page):
        page.goto(BASE_URL)
        nav = page.locator("nav.nav-links")
        expect(nav.get_by_role("link", name="Skills")).to_be_visible()
        expect(nav.get_by_role("link", name="Search")).to_be_visible()

    def test_home_has_sign_in_button(self, page: Page):
        page.goto(BASE_URL)
        expect(page.get_by_role("button", name="Sign in")).to_be_visible()

    def test_home_has_theme_toggle(self, page: Page):
        page.goto(BASE_URL)
        expect(page.get_by_role("button", name="Light theme")).to_be_visible()
        expect(page.get_by_role("button", name="Dark theme")).to_be_visible()

    def test_skills_page_loads(self, page: Page):
        page.goto(f"{BASE_URL}/skills")
        expect(page.locator("body")).to_contain_text(re.compile(r"skill", re.IGNORECASE))

    def test_search_page_loads(self, page: Page):
        page.goto(f"{BASE_URL}/search")
        expect(page.locator("body")).to_contain_text(re.compile(r"search", re.IGNORECASE))

    def test_404_spa_fallback(self, page: Page):
        """SPA routes should render (CloudFront serves index.html for unknown paths)."""
        resp = page.goto(f"{BASE_URL}/nonexistent-route")
        page.wait_for_timeout(2000)
        # CloudFront returns 200 (rewritten from 403/404) for SPA fallback
        assert resp is not None and resp.status == 200
        # Should render the app shell, not a raw XML error
        content = page.content()
        assert "<Error>" not in content


# ── 2. Navigation ───────────────────────────────────────────────────
class TestNavigation:
    def test_navigate_to_skills(self, page: Page):
        page.goto(BASE_URL)
        page.locator("nav.nav-links").get_by_role("link", name="Skills").click()
        page.wait_for_url(re.compile(r"/skills"))

    def test_navigate_to_search(self, page: Page):
        page.goto(BASE_URL)
        page.locator("nav.nav-links").get_by_role("link", name="Search").click()
        page.wait_for_url(re.compile(r"/search"))

    def test_brand_link_goes_home(self, page: Page):
        page.goto(f"{BASE_URL}/skills")
        page.locator(".brand").click()
        page.wait_for_url(re.compile(rf"^{re.escape(BASE_URL)}/?$"))


# ── 3. Login / Logout Flow ──────────────────────────────────────────
class TestLoginLogoutFlow:
    def test_login_modal_opens(self, page: Page):
        page.goto(BASE_URL)
        page.get_by_role("button", name="Sign in").first.click()
        expect(page.get_by_label("Username")).to_be_visible()
        expect(page.get_by_label("Password")).to_be_visible()

    def test_login_modal_cancel(self, page: Page):
        page.goto(BASE_URL)
        page.get_by_role("button", name="Sign in").first.click()
        page.get_by_role("button", name="Cancel").click()
        expect(page.get_by_label("Username")).not_to_be_visible()

    def test_login_with_wrong_password(self, page: Page):
        page.goto(BASE_URL)
        page.get_by_role("button", name="Sign in").first.click()
        page.get_by_label("Username").fill("admin")
        page.get_by_label("Password").fill("wrongpassword")
        page.locator("form").get_by_role("button", name="Sign in").click()
        expect(page.locator("text=Invalid username or password")).to_be_visible(timeout=10000)

    def test_successful_login(self, page: Page):
        page.goto(BASE_URL)
        login(page)
        expect(page.locator(".user-trigger")).to_contain_text("@admin")
        expect(page.get_by_role("button", name="Sign in")).not_to_be_visible()

    def test_user_dropdown_menu(self, page: Page):
        page.goto(BASE_URL)
        login(page)
        page.locator(".user-trigger").click()
        expect(page.get_by_role("button", name="Settings")).to_be_visible()
        expect(page.get_by_role("button", name="Admin", exact=True)).to_be_visible()
        expect(page.get_by_role("button", name="Sign out")).to_be_visible()

    def test_logout(self, page: Page):
        page.goto(BASE_URL)
        login(page)
        page.locator(".user-trigger").click()
        page.get_by_role("button", name="Sign out").click()
        expect(page.get_by_role("button", name="Sign in")).to_be_visible(timeout=10000)


# ── 4. Skills Browsing (Authenticated) ──────────────────────────────
class TestSkillsBrowsing:
    def test_skills_list_renders(self, page: Page):
        page.goto(BASE_URL)
        login(page)
        page.locator("nav.nav-links").get_by_role("link", name="Skills").click()
        page.wait_for_url(re.compile(r"/skills"))
        page.wait_for_timeout(3000)
        body_text = page.locator("body").inner_text()
        assert len(body_text) > 50

    def test_search_works(self, page: Page):
        page.goto(BASE_URL)
        login(page)
        page.locator("nav.nav-links").get_by_role("link", name="Search").click()
        page.wait_for_url(re.compile(r"/search"))
        page.wait_for_timeout(1000)
        search_input = page.locator("input").first
        search_input.fill("test")
        search_input.press("Enter")
        page.wait_for_timeout(3000)
        body_text = page.locator("body").inner_text()
        assert len(body_text) > 50


# ── 5. Admin Panel ──────────────────────────────────────────────────
class TestAdminPanel:
    def test_admin_page_loads(self, page: Page):
        page.goto(BASE_URL)
        login(page)
        page.goto(f"{BASE_URL}/admin")
        page.wait_for_timeout(3000)
        body_text = page.locator("body").inner_text().lower()
        assert "admin" in body_text

    def test_admin_nav_from_dropdown(self, page: Page):
        page.goto(BASE_URL)
        login(page)
        page.locator(".user-trigger").click()
        page.get_by_role("button", name="Admin", exact=True).click()
        page.wait_for_url(re.compile(r"/admin"))


# ── 6. Settings & API Key Management ────────────────────────────────
class TestSettingsPage:
    def test_settings_page_loads(self, page: Page):
        page.goto(BASE_URL)
        login(page)
        page.goto(f"{BASE_URL}/settings")
        expect(page.get_by_role("heading", name="Settings")).to_be_visible(timeout=10000)
        expect(page.get_by_role("heading", name="API Keys")).to_be_visible()

    def test_settings_nav_from_dropdown(self, page: Page):
        page.goto(BASE_URL)
        login(page)
        page.locator(".user-trigger").click()
        page.get_by_role("button", name="Settings").click()
        page.wait_for_url(re.compile(r"/settings"))
        expect(page.get_by_role("heading", name="API Keys")).to_be_visible()

    def test_generate_api_key(self, page: Page):
        page.goto(BASE_URL)
        login(page)
        page.goto(f"{BASE_URL}/settings")
        page.wait_for_timeout(3000)
        # Clean up if at key limit
        page.on("dialog", lambda dialog: dialog.accept())
        while page.get_by_role("button", name="Revoke").count() >= 10:
            page.get_by_role("button", name="Revoke").first.click()
            page.wait_for_timeout(1000)
        import uuid
        label = f"pw-gen-{uuid.uuid4().hex[:6]}"
        page.get_by_label("Label").fill(label)
        page.get_by_role("button", name="Generate new key").click()
        expect(page.locator("text=Copy it now")).to_be_visible(timeout=10000)
        expect(page.get_by_text(label).first).to_be_visible()

    def test_revoke_api_key(self, page: Page):
        page.goto(BASE_URL)
        login(page)
        page.goto(f"{BASE_URL}/settings")
        page.wait_for_timeout(3000)
        # Handle the confirm dialog
        page.on("dialog", lambda dialog: dialog.accept())
        # If there are existing keys, revoke one
        revoke_buttons = page.get_by_role("button", name="Revoke")
        count_before = revoke_buttons.count()
        if count_before == 0:
            # Create one first
            page.get_by_label("Label").fill("to-revoke")
            page.get_by_role("button", name="Generate new key").click()
            page.wait_for_timeout(3000)
            revoke_buttons = page.get_by_role("button", name="Revoke")
            count_before = revoke_buttons.count()
        revoke_buttons.first.click()
        page.wait_for_timeout(3000)
        count_after = page.get_by_role("button", name="Revoke").count()
        assert count_after < count_before

    def test_copy_button_present(self, page: Page):
        page.goto(BASE_URL)
        login(page)
        page.goto(f"{BASE_URL}/settings")
        page.wait_for_timeout(3000)
        # Revoke keys if at limit, then create a fresh one
        page.on("dialog", lambda dialog: dialog.accept())
        while page.get_by_role("button", name="Revoke").count() >= 10:
            page.get_by_role("button", name="Revoke").first.click()
            page.wait_for_timeout(1000)
        page.get_by_label("Label").fill("copy-test")
        page.get_by_role("button", name="Generate new key").click()
        expect(page.get_by_role("button", name="Copy")).to_be_visible(timeout=10000)

    def test_settings_requires_auth(self, page: Page):
        """Unauthenticated users should be redirected away from settings."""
        page.goto(f"{BASE_URL}/settings")
        page.wait_for_timeout(3000)
        expect(page.get_by_role("heading", name="API Keys")).not_to_be_visible()


# ── 7. Theme Switching ──────────────────────────────────────────────
class TestThemeSwitching:
    def test_switch_to_dark_theme(self, page: Page):
        page.goto(BASE_URL)
        page.get_by_role("button", name="Dark theme").click()
        html_class = page.locator("html").get_attribute("class") or ""
        html_data = page.locator("html").get_attribute("data-theme") or ""
        body_bg = page.locator("body").evaluate("el => getComputedStyle(el).backgroundColor")
        assert "dark" in html_class or "dark" in html_data or body_bg != "rgb(255, 255, 255)"

    def test_switch_to_light_theme(self, page: Page):
        page.goto(BASE_URL)
        page.get_by_role("button", name="Light theme").click()
        page.wait_for_timeout(500)
        # Light theme should render without error
        expect(page.locator("header")).to_be_visible()
