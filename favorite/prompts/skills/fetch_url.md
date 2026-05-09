# Skill: Fetch URL (§17.9)

  Fetches content from a URL and returns it to the agent.

  ## Usage

  ```
  «SKILL:name="fetch_url":url="https://example.com":max_chars=5000»
  ```

  ## Options

  - `url` — required, target URL
  - `max_chars` — max characters to return (default 5000)
  - `selector` — optional CSS selector to extract specific element
  - `mode` — "text" (default) or "markdown"

  ## Returned Format

  ```
  [FETCHED: https://example.com]
  <content>
  ```

  ## Notes

  - Respects robots.txt and rate limits
  - JavaScript-heavy pages may return incomplete content
  - For authenticated pages, the agent must handle auth first
  