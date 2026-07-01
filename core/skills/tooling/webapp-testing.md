---
name: webapp-testing
description: |
  Web application testing with Playwright.

  Use for:
  - Verifying frontend functionality
  - Debugging UI behavior
  - Capturing browser screenshots
  - Viewing browser logs
  - End-to-end testing

  Includes: Playwright patterns, server helpers, reconnaissance.
---

# Web Application Testing

Write native Python Playwright scripts.

## Decision Tree

```
Is it static HTML?
├─ Yes -> Read HTML directly, write Playwright script
└─ No (dynamic) -> Is server running?
    ├─ No -> Start server first, then test
    └─ Yes -> Reconnaissance-then-action pattern
```

## Basic Playwright Script

```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    page.goto('http://localhost:5173')
    page.wait_for_load_state('networkidle')  # CRITICAL!

    # Take screenshot
    page.screenshot(path='screenshot.png')

    # Get page content
    content = page.content()

    browser.close()
```

## Starting Server for Tests

```python
import subprocess
import time
import requests

# Start server
server = subprocess.Popen(
    ['npm', 'run', 'dev'],
    cwd='/path/to/project',
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE
)

# Wait for server to be ready
for _ in range(30):
    try:
        response = requests.get('http://localhost:5173')
        if response.status_code == 200:
            break
    except:
        pass
    time.sleep(1)

# Run tests...

# Cleanup
server.terminate()
```

## Reconnaissance Pattern

1. Navigate and wait for networkidle
2. Screenshot or inspect DOM
3. Identify selectors
4. Execute actions

```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    # 1. Navigate
    page.goto('http://localhost:5173')
    page.wait_for_load_state('networkidle')

    # 2. Reconnaissance
    page.screenshot(path='recon.png')
    print(page.title())

    # 3. Find selectors
    buttons = page.locator('button').all()
    print(f"Found {len(buttons)} buttons")

    # 4. Take action
    page.click('button:has-text("Submit")')

    browser.close()
```

## Common Actions

```python
# Click
page.click('button#submit')
page.click('text=Click me')
page.click('[data-testid="submit-btn"]')

# Fill input
page.fill('input[name="email"]', 'test@example.com')
page.fill('#password', 'secret123')

# Select dropdown
page.select_option('select#country', 'US')

# Check/uncheck
page.check('input[type="checkbox"]')
page.uncheck('input[type="checkbox"]')

# Type with keyboard
page.type('input', 'Hello', delay=100)
page.press('input', 'Enter')

# Wait for element
page.wait_for_selector('.loading', state='hidden')
page.wait_for_selector('.content', state='visible')

# Get text content
text = page.text_content('.result')
value = page.input_value('input#email')
```

## Assertions

```python
from playwright.sync_api import expect

# Element visibility
expect(page.locator('.success')).to_be_visible()
expect(page.locator('.error')).to_be_hidden()

# Text content
expect(page.locator('h1')).to_have_text('Welcome')
expect(page.locator('.count')).to_contain_text('5')

# Attribute
expect(page.locator('button')).to_be_enabled()
expect(page.locator('input')).to_have_value('test')

# URL
expect(page).to_have_url('http://localhost:5173/dashboard')
```

## Screenshots and Videos

```python
# Screenshot
page.screenshot(path='screenshot.png')
page.screenshot(path='full.png', full_page=True)

# Element screenshot
page.locator('.card').screenshot(path='card.png')

# Video recording
browser = p.chromium.launch()
context = browser.new_context(record_video_dir='videos/')
page = context.new_page()
# ... actions ...
context.close()  # Video saved on close
```

## Console Logs

```python
# Capture console messages
page.on('console', lambda msg: print(f'Console: {msg.text}'))

# Capture errors
page.on('pageerror', lambda err: print(f'Error: {err}'))

# Capture requests
page.on('request', lambda req: print(f'Request: {req.url}'))
page.on('response', lambda res: print(f'Response: {res.status}'))
```

## Common Pitfall

```python
# DON'T inspect DOM before networkidle
page.goto('http://localhost:5173')
print(page.content())  # May be incomplete!

# DO wait for networkidle first
page.goto('http://localhost:5173')
page.wait_for_load_state('networkidle')
print(page.content())  # Complete content
```

## Debug Mode

```python
# Run with headed browser
browser = p.chromium.launch(headless=False, slow_mo=500)

# Pause for debugging
page.pause()  # Opens inspector

# Trace for debugging
context = browser.new_context()
context.tracing.start(screenshots=True, snapshots=True)
# ... actions ...
context.tracing.stop(path='trace.zip')
# View with: playwright show-trace trace.zip
```

## Best Practices

1. **Always wait for networkidle** before interacting
2. **Use data-testid** for reliable selectors
3. **Screenshots for debugging** failed tests
4. **Headless by default**, headed for debugging
5. **Clean up** servers and browsers after tests
