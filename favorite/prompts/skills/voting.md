# Skill: Peer Voting (§18.6)

  Multi-main voting protocol for controversial decisions.

  ## Usage (Main Agent)

  ```
  «VOTE:question="Should we delete the old config file?":options="yes|no|defer":quorum=2»
  ```

  ## Voting Rules (§18.6)

  1. Quorum must be reached (default: majority of active mains)
  2. Each main agent sends one VOTE response
  3. The vote initiator collects and announces the result
  4. On tie: defer to the main with highest `peer_expertise_priority` for this topic

  ## Response Format (Peer)

  ```
  «PEER_REPLY:to="main-1":vote="yes"»I agree because the file is superseded by storage.json.«/PEER_REPLY»
  ```

  ## When to Use

  - Permanent deletion of files/data
  - Changing shared configuration that affects all mains
  - Architectural decisions with long-term impact
  - Any action tagged CRITICAL in the system prompt
  