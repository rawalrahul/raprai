---
name: refactoring-guide
description: "Identify code smells and suggest refactoring patterns (Extract Method, Strategy, Builder, etc.) with before/after code examples, risk assessment, and incremental step-by-step refactoring plans."
category: coding
difficulty: intermediate
model_boost: "Weak models suggest vague refactorings, don't show before/after code, miss risks, and propose risky rewrites instead of incremental changes"
---

# Refactoring Guide

## Purpose
Code that works but is hard to understand or modify accumulates technical debt. Refactoring improves code structure without changing behavior. This skill identifies code smells (symptoms of design problems), suggests specific patterns, shows incremental steps, and assesses risks—enabling confident, safe improvements.

## When to Use
- Before adding features to "smelly" code (extract logic first)
- When similar code appears in 3+ places (DRY principle)
- When functions exceed 25-30 lines (extract method)
- When tests are hard to write (code is too coupled)
- When class has 8+ instance variables (single responsibility violation)
- **Do NOT use when**: Code is stable, tested, and rarely touched (low ROI on refactoring), or during critical bug fixes

## Instructions

### Step 1: Identify Code Smells
Code smell = surface-level symptom suggesting deeper design issue. Common smells:

- **Long Method** (>25 lines): Too many responsibilities, hard to test, hard to reuse
- **Large Class** (8+ instance variables, 300+ lines): Violates single responsibility
- **Duplicate Code**: Appears in 2+ places, change in one place breaks another
- **Long Parameter List** (>4 parameters): Suggests missing abstraction, hard to test
- **Data Clumps** (same 3+ variables appear together): Missing class/object
- **Primitive Obsession** (int/string when should be object): Weak type safety
- **Switch Statements** (especially repeating): Suggests polymorphism instead
- **Divergent Change** (same class modified for different reasons): Wrong responsibilities
- **Shotgun Surgery** (change requires edits in many places): Responsibilities scattered
- **Feature Envy** (method uses another class's internals): Wrong class
- **Comments** (explaining what code does): Code should be self-documenting

Example of duplicate code smell:
```python
# Location 1: UserValidator.py
def validate_email(email):
    if '@' not in email or '.' not in email.split('@')[1]:
        raise ValueError("Invalid email")
    return True

# Location 2: FormHandler.py
def check_email(email):
    if '@' not in email or '.' not in email.split('@')[1]:
        raise ValueError("Invalid email format")
    return True
```

### Step 2: Suggest Refactoring Patterns
Match code smell to pattern:

| Smell | Pattern | Benefit |
|-------|---------|---------|
| Long method | Extract Method | Reusable, testable pieces |
| Duplicate code | Extract Method + DRY | Single source of truth |
| Large class | Extract Class | Single responsibility |
| Long parameter list | Introduce Parameter Object | Grouped data, easier to extend |
| Primitive types | Introduce Type/Value Object | Type safety, behavior |
| Switch statements | Replace with Polymorphism | Extensible without modifying code |
| Data clumps | Extract Class | Related data stays together |
| Divergent change | Extract Class | Clear responsibility boundaries |

Example: Extract Method Pattern
```python
# BEFORE: Long method doing multiple things
def process_order(order):
    # Validate order
    if not order['items']:
        raise ValueError("Order has no items")
    total = 0
    for item in order['items']:
        if item['quantity'] <= 0:
            raise ValueError("Invalid quantity")
        if item['price'] < 0:
            raise ValueError("Invalid price")
        total += item['quantity'] * item['price']

    # Apply discount
    if order['customer_type'] == 'premium':
        total = total * 0.9
    elif order['customer_type'] == 'member':
        total = total * 0.95

    # Save order
    db.save_order(order, total)
    send_confirmation_email(order)
    return total

# AFTER: Extracted methods
def process_order(order):
    validate_order(order)
    total = calculate_total(order)
    total = apply_discount(order, total)
    finalize_order(order, total)
    return total

def validate_order(order):
    if not order['items']:
        raise ValueError("Order has no items")
    for item in order['items']:
        if item['quantity'] <= 0 or item['price'] < 0:
            raise ValueError("Invalid item")

def calculate_total(order):
    return sum(item['quantity'] * item['price'] for item in order['items'])

def apply_discount(order, total):
    discounts = {
        'premium': 0.9,
        'member': 0.95,
        'standard': 1.0
    }
    return total * discounts.get(order['customer_type'], 1.0)

def finalize_order(order, total):
    db.save_order(order, total)
    send_confirmation_email(order)
```

### Step 3: Design Incremental Refactoring Plan
Never rewrite everything at once. Plan small, testable steps:

```
Step 1: Add tests for current behavior (ensure it's captured)
Step 2: Extract first small method (hardest logic first)
Step 3: Run tests → green
Step 4: Extract second method
Step 5: Run tests → green
Step 6: Consolidate similar methods
Step 7: Run tests → green
Step 8: Delete old code, update call sites
Step 9: Final test run
```

### Step 4: Assess Risk
Rate refactoring risk: GREEN (low), YELLOW (medium), RED (high)

Risk factors:
- **Test coverage** (>80% = GREEN, 50-80% = YELLOW, <50% = RED)
- **Number of call sites** (<5 = GREEN, 5-15 = YELLOW, >15 = RED)
- **Complexity of logic** (simple = GREEN, moderate = YELLOW, complex/nested = RED)
- **Criticality** (non-critical = GREEN, important = YELLOW, payment/auth = RED)

Example risk assessment:
```
Refactoring: Extract EmailValidator from UserService
Test Coverage: 92% ✓ GREEN
Call Sites: 3 (UserService, RegisterController, ProfileController) ✓ GREEN
Logic Complexity: Simple regex match + length check ✓ GREEN
Criticality: Authentication-adjacent ⚠ YELLOW
Overall Risk: GREEN (proceed with caution)
```

### Step 5: Provide Before/After Code
Show exact changes, not abstract descriptions:

```python
# BEFORE
class UserService:
    def register(self, email, password):
        if len(email) < 5 or '@' not in email:
            raise ValueError("Invalid email")
        if len(password) < 8:
            raise ValueError("Weak password")
        user = User(email, password)
        return self.db.save(user)

# AFTER
class EmailValidator:
    @staticmethod
    def validate(email):
        if len(email) < 5 or '@' not in email:
            raise ValueError("Invalid email")

class PasswordValidator:
    @staticmethod
    def validate(password):
        if len(password) < 8:
            raise ValueError("Weak password")

class UserService:
    def __init__(self, db):
        self.db = db
        self.email_validator = EmailValidator()
        self.password_validator = PasswordValidator()

    def register(self, email, password):
        self.email_validator.validate(email)
        self.password_validator.validate(password)
        user = User(email, password)
        return self.db.save(user)
```

### Step 6: Plan Call Site Updates
List every place that needs updating:

```
Extracting EmailValidator—Update these:
[ ] UserService.register() - line 45
[ ] ProfileController.updateEmail() - line 78
[ ] RegistrationForm.validateInput() - line 120
[ ] Tests: test_user_registration.py - lines 15, 32, 45
```

### Step 7: Execute Incrementally with Tests
1. Ensure tests pass before starting
2. Make one change
3. Run tests
4. Commit if green, investigate if red
5. Repeat until done

## Output Template

```
# Refactoring Plan: [Class/Method Name]

## Code Smells Identified
- [Smell 1]: [Location] [Impact]
- [Smell 2]: [Location] [Impact]

## Suggested Refactoring Pattern
**Pattern**: [Extract Method/Strategy/etc]
**Benefit**: [Outcome after refactoring]

## Risk Assessment
| Factor | Status | Notes |
|--------|--------|-------|
| Test Coverage | GREEN/YELLOW/RED | {{%}} covered |
| Call Sites | GREEN/YELLOW/RED | {{count}} locations |
| Logic Complexity | GREEN/YELLOW/RED | {{assessment}} |
| Criticality | GREEN/YELLOW/RED | {{impact if broken}} |
| **Overall** | **GREEN/YELLOW/RED** | {{summary}} |

## Incremental Refactoring Plan
**Step 1**: [First small refactoring]
**Step 2**: [Next small refactoring]
...

## Before/After Code

### Before
\`\`\`
[Original code]
\`\`\`

### After
\`\`\`
[Refactored code]
\`\`\`

## Call Sites to Update
- [ ] Location 1
- [ ] Location 2

## Testing Strategy
[How to verify refactoring didn't break anything]
```

## Quality Gates
- [ ] Code smell is specifically named, not vague ("bad design")
- [ ] Refactoring pattern is concrete (Extract Method, not just "improve code")
- [ ] Before/after code examples are shown in full, not pseudocode
- [ ] Risk assessment includes all 4+ factors with evidence
- [ ] Incremental plan is specific with exact steps, not abstract
- [ ] All call sites are identified, not just "update callers"

## Examples

### Good Output (excerpt)
```
## Code Smell: Duplicate Validation Logic
Found in:
- UserService.register() line 25
- ProfileController.updateEmail() line 78
- PasswordResetService.resetPassword() line 142

Exact duplication: Email validation appears identically in 3 places

## Suggested Pattern: Extract Method → Utility Class

## Risk Assessment
| Factor | Status | Reason |
|--------|--------|--------|
| Test Coverage | GREEN | 94% of UserService tested |
| Call Sites | YELLOW | 3 locations, all in same module |
| Logic Complexity | GREEN | Simple regex, no branches |
| Criticality | YELLOW | Email validation is in auth path |
| **Overall** | **YELLOW** | Proceed carefully; add tests for EmailValidator before extracting |

## Incremental Plan
1. Create EmailValidator class with validate() method
2. Add tests for EmailValidator (test all email formats)
3. Update UserService.register() to use EmailValidator
4. Run full test suite, commit
5. Update ProfileController.updateEmail()
6. Run tests, commit
7. Update PasswordResetService.resetPassword()
8. Final test run
9. Delete old validation code
```

### Bad Output (what to avoid)
```
"This code has bad design and duplicates. Extract it."
```
Vague smell, no pattern, no plan, no before/after, no risk assessment.

## Common Mistakes

1. **Mistake**: Refactoring without tests; breaking code silently
   → **Fix**: Write tests first (even for existing code). Refactoring with green tests is safe.

2. **Mistake**: Proposing a complete rewrite instead of incremental steps
   → **Fix**: Break into 5-10 small changes, each tested. Safer and easier to understand.

3. **Mistake**: Extracting without identifying all call sites; some code still calls old way
   → **Fix**: Search codebase for every reference. Update all or keep both temporarily.

4. **Mistake**: Missing that refactoring changes performance; extract method adds overhead
   → **Fix**: Benchmark critical paths before and after. Sometimes not refactoring is correct.

5. **Mistake**: Ignoring that extracted code needs the same tests as original
   → **Fix**: Write tests for extracted pieces, not just original function.

## Anti-Patterns

- Never refactor and fix bugs at the same time; changes become impossible to understand
- Never extract a method and then realize it needs 10 parameters; this suggests wrong abstraction—reconsider
- Never refactor code without understanding why it exists; that "duplicate" might be intentionally separate for different reasons
- Never leave partially refactored code; old and new both exist, confusing readers
- Never refactor code that has zero tests; add tests first, then refactor safely

