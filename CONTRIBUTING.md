# How we work (branches)

## Branches
- `main`: always working. Only merged code goes here.
- `kripas-backend`: Kripas works here (`backend/`).
- `friend-frontend`: [Friend's name] works here (`frontend/`).

Each person mostly touches only their own folder, so merges are easy. Shared files (`notes/LEARNING_LOG.md`, `docs/`) can be edited by both. Pull before editing them.

## First time (each person)
```bash
git clone https://github.com/kripas1369/wise-blink-practice.git
cd wise-blink-practice
git checkout kripas-backend      # Kripas
git checkout friend-frontend     # friend
```

## Every session
```bash
git checkout <your-branch>
git pull origin main             # get the other person's merged work
# ... work ...
git add -A
git commit -m "Day N: what you did"
git push
```

## End of each day: merge into main
1. On GitHub, open a **Pull Request** from your branch into `main`.
2. The other person looks at it quickly (or the AI reviews it).
3. Merge it. Then both run `git pull origin main` on their branch next session.

## Rules
- Tests for finished days must pass before merging into `main` (`python -m pytest backend/tests`). Tests for a day not yet done are expected to fail.
- Small commits with clear messages ("Day 3: flipbook play/pause").
- No fake values; every number on screen comes from data.
- Practice code is never copied into the hackathon repo; on 14 Nov we write it again from memory.
