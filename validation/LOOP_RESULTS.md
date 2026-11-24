# Historical learning-loop result

This transcript predates the final audit fixes. It entered Git at `70a385f14f2a357f562afb54ddd8c85627776fb8`.

The current harness checks exact note state, source fields and successful tool calls. It has not had a paid rerun. The result below belongs to the earlier harness. Its transcript body is unchanged.

Every answer below is the real output of `validation/twin_loop.py`: fresh `claude` sessions on a throwaway twin with the made-up sample notes. One run. A model's wording varies from run to run.

**7 of 7 checked steps came out as expected.**

## 1. Fresh session, no twin

```
I don't know. I have no notes or files in this session that mention your shipping label colour, and I won't guess.
```

As expected.

## 2. Fresh session, with the twin, before any note exists

```
I don't know. The twin has no notes on what colour you print shipping labels in.
```

As expected.

## 3a. The owner corrects it, and a session proposes the note

```
I proposed a taste note to the twin: "Shipping labels are printed in black only." The owner still has to accept it in the twin page.
```

## 3b. The owner accepts it

```
Shipping labels are printed in black only.
```

As expected.

## 4. Another fresh session

```
Black only (source: your twin note, "Shipping labels are printed in black only," dated 2026-11-24).
```

As expected.

## 5a. The owner changes the decision, and a session proposes it

```
I proposed a brand-scope taste note, "Shipping labels are printed in dark green, not black", and it's waiting for the owner to accept it in the twin page.
```

## 5b. The owner picks Replace the old one

```
Shipping labels are printed in dark green, not black (owner's decision, effective now). | clashes with: Shipping labels are printed in black only.
{'ok': 1}
```

As expected.

## 6. Another fresh session

```
Dark green, not black. This replaced the old black-only rule on 2026-11-24. Source: your twin (claude-code), brand-scope note.
```

As expected.

## 6b. What the twin holds now

```
Shipping labels are printed in dark green, not black (owner's decision, effective now).
```

As expected.

## The twin's own log

```
2026-11-24T13:24:19 | proposal accepted | from claude-code | personal | Shipping labels are printed in black only.
2026-11-24T13:24:27 | note replaced | Shipping labels are printed in black only. -> Shipping labels are printed in dark green, not black (owner's decision, effective now).
2026-11-24T13:24:27 | proposal accepted | from claude-code | brand | Shipping labels are printed in dark green, not black (owner's decision, effective now).
```

## Who asked

```
[{"name": "claude-code", "last_tool": "twin_recall", "calls": 5}]
```
