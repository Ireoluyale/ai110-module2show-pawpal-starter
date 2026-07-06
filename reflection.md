# PawPal+ Project Reflection

## 1. System Design

**a. Initial design**

- Briefly describe your initial UML design.
- What classes did you include, and what responsibilities did you assign to each?
Pet-Stores info about the user's pet
Owner-Stores preferences about the Pet's owner
CareTask-Holds details about each care task




Core actions a User can peform
-Log pet bio/info ( name, etc)
-Schedule tasks
-Recommend actions based on use patterns

**b. Design changes**

- Did your design change during implementation?
- If yes, describe at least one change and why you made it.

---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

- What constraints does your scheduler consider (for example: time, priority, preferences)?
- How did you decide which constraints mattered most?

**b. Tradeoffs**

- Describe one tradeoff your scheduler makes.
- Why is that tradeoff reasonable for this scenario?

---

## 3. AI Collaboration

**a. How you used AI**

- How did you use AI tools during this project (for example: design brainstorming, debugging, refactoring)?
I used AI to suggest attributes for the maon classes and why they will be useful to the flow of the app
- What kinds of prompts or questions were most helpful?
prompts for the UML diagram were useful to me beause I found it a bit confusing to perform manually

**b. Judgment and verification**

- Describe one moment where you did not accept an AI suggestion as-is.
- How did you evaluate or verify what the AI suggested?

---

## 4. Testing and Verification

**a. What you tested**

- What behaviors did you test?

I wrote five tests covering the core behaviors of the system:

1. **Marking a task complete** — `mark_complete()` flips a task from pending to
   done.
2. **Attaching a task to a pet** — adding a task grows that pet's task list by
   one and links it to the pet.
3. **Sorting by time** — `sort_by_time()` returns tasks earliest-first even when
   they were added out of order (including `"09:00"` without special handling).
4. **Daily recurrence** — completing a daily task spawns a fresh, incomplete
   copy due the next day, with a new id, leaving two tasks on the pet.
5. **Conflict detection** — `find_conflicts()` groups tasks that share the same
   date and time (Rex and Milo both at 08:00) while ignoring non-clashing tasks.

- Why were these tests important?

These behaviors are the heart of the scheduler, so a silent bug in any of them
would make the daily plan wrong without an obvious crash:

- The **sorting** test guards the numeric-minutes key: a naive string sort would
  place `"9:00"` after `"18:00"`, quietly ordering the day incorrectly. This test
  proves the ordering logic, not just Python's `sorted()`.
- The **recurrence** test verifies that a completed daily task actually
  regenerates for the next day (and that the copy is a distinct, incomplete task,
  not a mutation of the original) — the mechanism that keeps a routine going.
- The **conflict** test confirms the scheduler both catches real clashes and
  does *not* raise false alarms on tasks at different times, which is what makes
  the conflict warnings trustworthy.
- The **status** and **attachment** tests lock down the small state changes every
  other feature is built on, so a regression there is caught immediately.

**b. Confidence**

- How confident are you that your scheduler works correctly?
I'm confident in the paths my tests cover — sorting, recurrence, conflict
detection, and the basic state changes all pass. I'm less certain about untested
edge cases like three-way conflicts, weekly recurrence, and bad input, which is
where I'd focus next.

- What edge cases would you test next if you had more time?
More scheduling conflicts, 3 or more
---

## 5. Reflection

**a. What went well**

- What part of this project are you most satisfied with?
The class creation and implementation phases were very smooth and worked as I would like

**b. What you would improve**

- If you had another iteration, what would you improve or redesign?
The UI elements of the app

**c. Key takeaway**

- What is one important thing you learned about designing systems or working with AI on this project?
Testing is a very underrated paart of design and I'm grateful AI can assist with it
