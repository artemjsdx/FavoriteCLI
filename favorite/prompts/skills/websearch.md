# Skill: Web Search (§17.8)

  This skill provides web search capability via the SKILL tag.

  ## Usage

  ```
  «SKILL:name="websearch":query="your query here":max_results=5»
  ```

  ## Returned Format

  ```
  [SEARCH RESULTS: "query"]
  1. Title — URL
     Snippet...
  2. ...
  ```

  ## Notes

  - Uses the configured search provider (brave/duckduckgo/serper)
  - max_results: 1-10, default 5
  - Results are injected as system message to the agent
  - Subsequent turns can reference the results by URL

  ## When to Use

  - User asks about current events (after your knowledge cutoff)
  - Need to verify facts or find documentation
  - Looking for code examples, packages, or APIs
  