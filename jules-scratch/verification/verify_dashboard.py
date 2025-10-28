from playwright.sync_api import sync_playwright, Page, expect

def run_verification():
    """Navigates to the app and takes a screenshot of the dashboard."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        try:
            # Go to the application's homepage
            page.goto("http://localhost:5000", timeout=30000) # Increased timeout

            # Wait for a key element of the dashboard to be visible
            # This ensures the page is fully loaded before taking a screenshot
            dashboard_header = page.get_by_role("heading", name="Dashboard")
            expect(dashboard_header).to_be_visible(timeout=10000)

            # Take a screenshot of the page
            page.screenshot(path="jules-scratch/verification/dashboard.png")
            print("Screenshot 'dashboard.png' created successfully.")

        except Exception as e:
            print(f"An error occurred during verification: {e}")
            # Try to capture the page content for debugging
            try:
                page.screenshot(path="jules-scratch/verification/error.png")
                print("An error screenshot was captured.")
            except Exception as ss_err:
                print(f"Could not even take an error screenshot: {ss_err}")

        finally:
            browser.close()

if __name__ == "__main__":
    run_verification()
