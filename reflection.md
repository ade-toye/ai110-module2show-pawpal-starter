# PawPal+ Project Reflection

## 1. System Design

**a. Initial design**

- Briefly describe your initial UML design.
We will definitely need a Pet class, Constraint, Daily Planner and AI Assistant
- What classes did you include, and what responsibilities did you assign to each?
The Pet class would be there in case the user has multiple pets, 
The constraint class is there to enter our ysers availability
The daily planner class is the class that captures the finalized schedule for the day
The AI Assistan class is the one that acts as the "brain" of your Streamlit app, processing input data to produce the final plan.

**b. Design changes**

- Did your design change during implementation?
Not really
- If yes, describe at least one change and why you made it.
The design remained the same but it added the missing bottlenecks. 

---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

- What constraints does your scheduler consider (for example: time, priority, preferences)?
- How did you decide which constraints mattered most?

**b. Tradeoffs**

- Describe one tradeoff your scheduler makes.

The scheduler checks for conflicts by comparing a task's `end_time` string against the next task's `start_time` string for the same pet. This catches overlaps between **adjacent** slots in the sorted list, but it assumes the list is already in time order and only inspects neighboring pairs — it does not perform an exhaustive all-pairs overlap check across every combination of tasks.

- Why is that tradeoff reasonable for this scenario?

In a correctly sorted schedule, if task A ends after task B starts, those two are the only pair that can overlap at that boundary — a third task C further down the list cannot create a conflict that A and B don't already expose. Checking only adjacent pairs after sorting is therefore both correct and efficient: it reduces the conflict scan from O(n²) (all-pairs) down to O(n) (one linear pass). For a daily pet care schedule with a small number of tasks per pet, this keeps the algorithm fast and the code easy to read without sacrificing correctness.

---

## 3. AI Collaboration

**a. How you used AI**

- How did you use AI tools during this project (for example: design brainstorming, debugging, refactoring)?
- What kinds of prompts or questions were most helpful?

**b. Judgment and verification**

- Describe one moment where you did not accept an AI suggestion as-is.
- How did you evaluate or verify what the AI suggested?

---

## 4. Testing and Verification

**a. What you tested**

- What behaviors did you test?
- Why were these tests important?

**b. Confidence**

- How confident are you that your scheduler works correctly?
- What edge cases would you test next if you had more time?

---

## 5. Reflection

**a. What went well**

- What part of this project are you most satisfied with?

**b. What you would improve**

- If you had another iteration, what would you improve or redesign?

**c. Key takeaway**

- What is one important thing you learned about designing systems or working with AI on this project?
