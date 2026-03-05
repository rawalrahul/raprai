---
name: chatbot-conversation-designer
description: "Design production-ready chatbot conversations with intent taxonomies, entity extraction schemas, dialog state machines, multi-turn memory, slot-filling patterns, and escalation triggers. Build robust NLU training data and error recovery flows."
category: ai-automation
difficulty: intermediate
model_boost: "Fixes shallow chatbot conversations that lack intent understanding, get stuck on edge cases, and fail to gracefully handle user corrections"
---

# Chatbot Conversation Designer

## Purpose
This skill teaches you to architect sophisticated chatbot conversations that understand user intent, extract entities, maintain state across turns, handle ambiguity, and gracefully escalate to humans. You'll design intent taxonomies, entity schemas, dialog state machines, confirmation strategies, and personality guides. The output is production-ready conversation flows with NLU training data, error paths, and measurable quality metrics.

## When to Use
- Building conversational interfaces (customer support, sales, onboarding)
- Designing multi-turn dialogs requiring context and state management
- Creating NLU models for intent/entity recognition
- Planning escalation paths from bot to human agent
- Defining fallback strategies for out-of-scope requests
- **Do NOT use when**: Single-turn, single-intent interactions (use simple prompt instead), or conversations with no ambiguity/error cases

## Instructions

### Step 1: Define Intent Taxonomy and Coverage
Create a hierarchical classification of what users want to say and do.

**Intent Structure** (3-level hierarchy):
```yaml
intents:
  commerce:
    purchase:
      browse_products
      add_to_cart
      checkout
      apply_coupon
    returns:
      initiate_return
      check_return_status
      request_refund
  support:
    technical:
      report_bug
      request_feature
      troubleshoot_issue
    account:
      reset_password
      update_profile
      check_subscription_status
  information:
    general_question
    pricing_inquiry
    faq_lookup
  off_scope:
    small_talk
    profanity
    harassment
```

**Intent Definition Template** (for each intent):
```yaml
intent: purchase_browsing
parent_category: commerce.purchase
description: "User wants to search, filter, or view products"
examples:
  - "Show me laptops under $1000"
  - "Do you have this in blue?"
  - "What are your best-selling items?"
  - "Can I filter by brand?"
required_entities:
  - product_category (optional)
  - price_range (optional)
  - product_attribute (optional)
expected_response_type: product_listing
success_criterion: "User sees relevant products or clarification question"
escalation_trigger: "User says 'I don't see what I want' after 3 product listings"
```

**Coverage Analysis** (ensure comprehensive taxonomy):
```
Total intents: 35
Training data distribution:
  commerce: 45% (15 intents)
  support: 35% (12 intents)
  information: 15% (6 intents)
  off_scope: 5% (2 intents)

Confidence targets:
  High-confidence (user satisfaction):
    - commerce.purchase intents: >= 90% accuracy
    - support.account intents: >= 85% accuracy
  Medium-confidence (review before action):
    - support.technical intents: >= 80% accuracy
  Low-confidence (human review required):
    - Off-scope intents: >= 95% precision (minimize false positives)
```

**Intent Confusion Matrix** (identify hard-to-distinguish pairs):
```
Confusions to watch:
  browse_products vs general_question:
    - User says "What's popular?" - Intent: browse_products (they want to see items)
    - User says "What should I get?" - Intent: could be general_question or browse_products
    - Clarification: "Are you looking to browse our catalog?"

  troubleshoot_issue vs report_bug:
    - troubleshoot_issue: User experiencing problem, wants help to fix
    - report_bug: User found software defect, reporting for engineering
    - Disambiguation: "Are you having this issue yourself, or reporting a product defect?"
```

### Step 2: Design Entity Extraction Schema
Define what structured data to extract from user messages.

**Entity Types** (semantic categories):
```yaml
entities:
  product:
    product_id: string
    product_name: string
    product_category: enum [laptops, phones, tablets, accessories]
    product_attribute: string (color, size, material)
  user:
    user_id: string (internal, not extracted from chat)
    email: email_regex
    phone: phone_regex
    name: string
  transaction:
    order_id: string
    price_range: [min_usd, max_usd]
    quantity: integer
    coupon_code: string (alphanumeric)
  temporal:
    date: ISO_8601 date
    time: HH:MM in 24h format
    relative_time: enum [today, tomorrow, this week, asap]
```

**Extraction Rules** (with examples):
```python
extract_email:
  pattern: /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/
  example_input: "Email me at support@company.com"
  expected_output: {"entity_type": "email", "value": "support@company.com", "confidence": 0.99}

extract_product_category:
  # Keyword-based extraction (simple)
  keywords:
    laptops: ["laptop", "computer", "macbook", "notebook", "lenovo", "dell"]
    phones: ["phone", "smartphone", "iphone", "pixel", "android"]
  example: "Do you have any gaming laptops?"
  expected: {"entity_type": "product_category", "value": "laptops"}

extract_price_range:
  # Pattern: "$XXX to $YYY" or "under $XXX"
  pattern_1: /\$(\d+)\s*(?:to|-)\s*\$(\d+)/
  pattern_2: /(?:under|below|max|limit)\s*\$(\d+)/
  example: "Show me phones under $500"
  expected: {"entity_type": "price_range", "value": [0, 500]}

extract_quantity:
  pattern: /(?:^|\s)(\d+)\s*(?:items?|units?|pieces?)?(?:\s|$)/
  example: "I need 5 laptop chargers"
  expected: {"entity_type": "quantity", "value": 5}
```

**Entity Confidence & Ambiguity Handling**:
```python
# If extraction confidence < threshold, ask for clarification
if entity_confidence < 0.75:
    clarify_prompt = f"Did you mean {extracted_value}?"
    # Example: Extract price "1000" - could be $1000 or 10.00
    clarify_prompt = "Did you mean $1,000 or $100?"

# Ambiguous entity references (pronoun resolution)
user_turn_1: "I want a laptop with 16GB RAM"
user_turn_2: "Does it come in silver?"
# Context: "it" = laptop from turn 1, carry forward product_category: laptops
```

**Multi-Entity Extraction** (combined):
```
User: "I want to return order ABC123 from 2 weeks ago"
Extracted: {
  intent: "initiate_return",
  entities: {
    order_id: "ABC123",
    relative_time: "2 weeks ago",
    purchase_date: <calculated from relative_time>
  }
}

User: "Show me silver laptops under $1000 in stock today"
Extracted: {
  intent: "browse_products",
  entities: {
    product_category: "laptops",
    product_attribute: "silver",
    price_range: [0, 1000],
    availability_status: "in_stock",
    temporal: "today"
  }
}
```

### Step 3: Design Dialog State Machine
Map out conversation flow as explicit state transitions.

**State Definitions** (simplified example for "purchase" flow):
```yaml
states:
  START:
    description: "Initial state, waiting for user input"
    transitions:
      - on_intent: browse_products → BROWSING
      - on_intent: checkout → ASK_AUTHENTICATION
      - on_intent: off_scope → OFF_SCOPE_HANDLER

  BROWSING:
    description: "User browsing products, may filter/search"
    data_required: [product_category]
    transitions:
      - on_intent: add_to_cart → CONFIRM_ADD
      - on_intent: apply_filter → BROWSING (stay, update filters)
      - on_intent: proceed_to_checkout → ASK_AUTHENTICATION
      - on_no_match: 3 times → ESCALATE_TO_HUMAN

  CONFIRM_ADD:
    description: "Confirm product addition before updating cart"
    data_required: [product_id, quantity]
    transitions:
      - on_user_confirm: → CART_UPDATED
      - on_user_cancel: → BROWSING
      - timeout (30s): → BROWSING

  CART_UPDATED:
    description: "Item added to cart, ask next action"
    transitions:
      - on_intent: continue_shopping → BROWSING
      - on_intent: checkout → ASK_AUTHENTICATION

  ASK_AUTHENTICATION:
    description: "Verify user identity before checkout"
    transitions:
      - on_auth_success: → CONFIRM_CHECKOUT
      - on_auth_failure: → ASK_AUTHENTICATION (retry)
      - after_3_failures: → ESCALATE_TO_HUMAN

  CONFIRM_CHECKOUT:
    description: "Final review before payment"
    transitions:
      - on_confirm: → PROCESS_PAYMENT
      - on_cancel: → BROWSING

  PROCESS_PAYMENT:
    description: "Payment processing (no user input)"
    transitions:
      - on_success: → CHECKOUT_SUCCESS
      - on_failure: → PAYMENT_ERROR

  CHECKOUT_SUCCESS:
    description: "Order confirmed, show confirmation"
    transitions:
      - on_done: → CONVERSATION_END

  ESCALATE_TO_HUMAN:
    description: "Transfer to human agent"
    action: "Queue to support_queue, send context to agent"
    transitions:
      - agent_accepted: → HANDED_OFF
      - timeout (5m): → OFFER_CALLBACK

  OFF_SCOPE_HANDLER:
    description: "Handle requests outside domain"
    transitions:
      - on_small_talk: Acknowledge, redirect → START
      - on_harassment: End conversation → CONVERSATION_END
```

**State Diagram** (ASCII representation):
```
START
  ├─ browse_products → BROWSING ──┐
  ├─ checkout → ASK_AUTHENTICATION │
  └─ off_scope → OFF_SCOPE_HANDLER │
                                   ├─ BROWSING ──────────────┐
                                   │  ├─ add_to_cart         │
                                   │  ├─ apply_filter (loop) │
                                   │  └─ 3 no_matches → ESC  │
                                   │                          ├─ CONFIRM_ADD ── ASK_CART_ACTION
                                   │                          │
                                   └─ checkout → ASK_AUTH ────┴─ CONFIRM_CHECKOUT
                                                   ├─ auth_success
                                                   └─ auth_failure (retry)
                                                         │
                                                    PROCESS_PAYMENT
                                                    ├─ success → CHECKOUT_SUCCESS
                                                    └─ failure → PAYMENT_ERROR

ESCALATE_TO_HUMAN
  ├─ agent_accepted → HANDED_OFF
  └─ timeout → OFFER_CALLBACK
```

**Context Preservation Across States**:
```python
class DialogContext:
    def __init__(self):
        self.state: str = "START"
        self.user_id: str = None
        self.session_id: str = generate_uuid()
        self.turn_count: int = 0
        self.intents_history: list = []
        self.entities_extracted: dict = {}  # Carries across states
        self.cart_items: list = []
        self.created_at: timestamp = now()
        self.last_update: timestamp = now()

    def update_state(self, new_state: str, intent: str = None, entities: dict = None):
        self.state = new_state
        if intent:
            self.intents_history.append(intent)
        if entities:
            self.entities_extracted.update(entities)
        self.last_update = now()
```

### Step 4: Define Conversation Flows (Happy Path + Error Paths)
Write out complete conversation scripts for key scenarios.

**Happy Path: Browse & Purchase**
```
User: "Show me gaming laptops under $2000"
Bot:
  - intent: browse_products
  - entities: {product_category: "laptops", price_range: [0, 2000]}
  - query: SELECT * FROM products WHERE category='laptops' AND price < 2000 AND gaming=true
  - response: "I found 23 gaming laptops under $2000. Here are my top 5 recommendations: [list]"

User: "Tell me more about the first one"
Bot:
  - intent: product_inquiry
  - entities: {product_reference: "first", ordinal: 1}
  - resolve_reference: products[0] → ASUS TUF A16 RTX4070 $1899
  - response: "[Full product specs: processor, RAM, storage, GPU, display, weight, warranty]"

User: "Does it have WiFi 6?"
Bot:
  - intent: product_inquiry (specific feature)
  - entities: {product_attribute: "wifi_6"}
  - check_specs: ASUS TUF A16 has WiFi 6E ✓
  - response: "Yes! This model has WiFi 6E for faster wireless speeds."

User: "I'll take it"
Bot:
  - intent: add_to_cart
  - entities: {product_id: "ASUS_TUF_A16", quantity: 1 (default)}
  - response: "Adding ASUS TUF A16 to your cart. Would you like to continue shopping or proceed to checkout?"

User: "Let's checkout"
Bot:
  - intent: checkout
  - action: Check user auth status
  - if not_authenticated: Redirect to login/SSO
  - response: "Great! I'm verifying your account. [OAuth flow]"

User: [Logs in]
Bot:
  - action: Retrieve cart items, apply loyalty discounts, calculate tax/shipping
  - response: "Order summary:\n- ASUS TUF A16: $1,899\n- Shipping: $25\n- Tax: $189\n- Total: $2,113\n\nConfirm purchase?"

User: "Yes, confirm"
Bot:
  - intent: confirm_order
  - action: PROCESS_PAYMENT → charge credit card
  - response: "✓ Order confirmed! Order #ORD-123456. Confirmation sent to your email."
```

**Error Path 1: Product Not Found**
```
User: "Show me VR headsets"
Bot:
  - intent: browse_products
  - entities: {product_category: "vr_headsets"}
  - query: SELECT * FROM products WHERE category='vr_headsets'
  - result: Empty (category not in catalog)
  - response: "We don't currently carry VR headsets. But we do have laptops, phones, and tablets. Interested in any of those?"

User: "No, that's all I came for"
Bot:
  - intent: off_scope / end_conversation
  - action: Log interaction, offer feedback survey
  - response: "Got it! Before you go, would you consider leaving feedback about products you'd like us to carry?"
```

**Error Path 2: Ambiguous Reference**
```
User: "I want the red one"
Bot:
  - intent: add_to_cart
  - entities: {product_reference: "red one"}
  - error: Can't resolve reference (no context or multiple red products)
  - response: "I see a few red options. Did you mean:\n1) Red laptop (ASUS, $999)\n2) Red phone case ($29)\n3) Red tablet ($649)"

User: "The first one"
Bot:
  - intent: add_to_cart (with clarification)
  - entities: {product_id: "ASUS_RED_LAPTOP", ordinal: 1}
  - action: Add to cart
  - response: "Added ASUS Red Laptop to your cart!"
```

**Error Path 3: Authentication Failure**
```
User: "Let's checkout"
Bot:
  - intent: checkout
  - action: Attempt OAuth login
  - result: Login failed (password incorrect)
  - response: "Login unsuccessful. Let me try again. [Password reset link]"

User: [Clicks password reset, completes it]
Bot:
  - action: Retry login with new password
  - result: Login successful
  - response: "Welcome back! Proceeding to checkout..."

[If fails 3x]
Bot:
  - intent: escalate_to_human
  - response: "I'm having trouble logging you in. Let me connect you with a support agent who can help."
  - action: Queue to support_queue with context
```

### Step 5: Design Slot-Filling Patterns
Explicitly manage multi-turn dialogs where you need to collect information.

**Restaurant Booking Example** (requires 4 slots):
```python
class SlotFillingDialog:
    required_slots = {
        "date": {"type": "date", "prompt": "What date would you like?"},
        "time": {"type": "time", "prompt": "What time works for you?"},
        "party_size": {"type": "integer", "prompt": "How many people?"},
        "dietary_restrictions": {"type": "list", "prompt": "Any dietary restrictions?", "required": False}
    }

    def fill_slots(user_input: str, filled_slots: dict) -> dict:
        """Extract any mentioned slots from user input"""
        entities = extract_entities(user_input)

        for entity in entities:
            if entity.type in required_slots:
                filled_slots[entity.type] = entity.value

        return filled_slots

    def get_next_prompt(filled_slots: dict) -> str:
        """Find first unfilled required slot"""
        for slot_name, slot_config in required_slots.items():
            if slot_name not in filled_slots:
                return slot_config["prompt"]
        return None  # All slots filled
```

**Example Dialog**:
```
Bot: "I'd be happy to help you book a table! What date would you like?"
User: "Tomorrow at 7pm for 4 people"
Bot:
  - extract_entities: {date: tomorrow, time: 19:00, party_size: 4}
  - filled_slots: {date, time, party_size}
  - next_unfilled: None
  - response: "Great! Let me search for a table tomorrow at 7pm for 4 people. Any dietary restrictions I should know about?"

User: "My friend is vegetarian"
Bot:
  - extract_entities: {dietary_restrictions: [vegetarian]}
  - filled_slots: {date, time, party_size, dietary_restrictions}
  - all_slots_filled: True
  - action: Query restaurant database with filters
  - response: "Perfect! I found 3 restaurants with vegetarian options for tomorrow 7pm, 4 people:\n[List with availability]"
```

**Edge Case: Over-Specification**
```
User: "I want a table on January 15th at 6pm for 2 people and I'm vegetarian"
Bot:
  - extract_entities: {date, time, party_size, dietary_restrictions}
  - All slots filled in single turn ✓
  - response: "Great! Checking availability for Jan 15 at 6pm for 2 vegetarians..."
  - (No need for follow-up prompts)
```

### Step 6: Design Confirmation and Clarification Strategies
Explicitly handle uncertainty without being annoying.

**Confirmation Thresholds**:
```python
# Only ask confirmation if confidence is low
confidence_threshold = 0.80

# High confidence: proceed without confirmation
if intent_confidence >= 0.95 and entity_confidence >= 0.90:
    action = "proceed"  # No confirmation needed

# Medium confidence: ask for clarification
elif intent_confidence >= 0.80 and entity_confidence >= 0.80:
    action = "proceed_with_note"  # Proceed but log for review

# Low confidence: ask user to confirm
else:
    action = "ask_clarification"
    prompt = generate_clarification_prompt()
```

**Clarification Types**:
```yaml
type_1_intent_clarification:
  description: "Confirm user's intent"
  trigger: "Intent confidence < 75%"
  examples:
    - input: "My order isn't working"
    - possible_intents: [report_bug, troubleshoot_issue, refund_request]
    - clarification: "Are you experiencing a technical issue, or do you want to cancel your order?"

type_2_entity_clarification:
  description: "Confirm entity interpretation"
  trigger: "Entity confidence < 75%"
  examples:
    - input: "I want the blue thing"
    - entities_found: {product_attribute: blue, product_reference: ambiguous}
    - clarification: "Do you mean the blue phone case or blue laptop sleeve?"

type_3_reference_resolution:
  description: "Resolve pronouns or ambiguous references"
  trigger: "Can't resolve 'it', 'that', 'this' to previous product"
  examples:
    - history: [User asked about iPhone 15, then Samsung S24]
    - input: "Does it support 5G?"
    - clarification: "Do you mean the iPhone 15 or Samsung S24?"

type_4_implicit_requirement:
  description: "Clarify assumed requirements"
  trigger: "User's request may have implicit constraints"
  examples:
    - input: "Book me a flight to NYC"
    - implicit: [departure_city, departure_date, return_date, budget]
    - clarification: "Where are you flying from, and what date?"
```

### Step 7: Design Escalation Triggers and Handoff Protocol
Define when and how to transfer to human agents.

**Escalation Triggers** (escalate when):
```python
escalation_rules = {
    "low_nlu_confidence": {
        "trigger": "intent_confidence < 0.6",
        "count_threshold": 2,  # After 2 failed turns
        "message": "I'm having trouble understanding. Let me connect you with an agent."
    },
    "user_frustration": {
        "trigger": "User says: 'This isn't working', 'Talk to someone', 'I want a human'",
        "immediate": True,
        "message": "Of course! Connecting you with a specialist now."
    },
    "sensitive_data": {
        "trigger": "User mentions SSN, credit card details, passport number",
        "immediate": True,
        "action": "Disable collection, escalate immediately",
        "message": "For security, please discuss sensitive information with an agent."
    },
    "out_of_scope": {
        "trigger": "Intent is 'off_scope' and not small_talk",
        "count_threshold": 1,
        "message": "That's outside my expertise. Let me get you to someone who can help."
    },
    "task_complexity": {
        "trigger": "Conversation involves > 5 turns or multiple requests",
        "message": "This sounds complex. Would you prefer to speak with an agent?"
    }
}
```

**Handoff Protocol**:
```python
class EscalationHandler:
    async def escalate_to_human(self, context: DialogContext, reason: str):
        """Transfer conversation to human agent"""

        # Step 1: Prepare context for agent
        handoff_packet = {
            "session_id": context.session_id,
            "user_id": context.user_id,
            "conversation_history": context.intents_history,
            "extracted_entities": context.entities_extracted,
            "escalation_reason": reason,
            "escalation_timestamp": now(),
            "bot_confidence_summary": {
                "last_intent_confidence": 0.55,
                "entity_extraction_success": 0.70,
            },
            "recommended_action": "Review and assist with account issue"
        }

        # Step 2: Route to appropriate queue
        queue = route_to_queue(context)
        await queue.enqueue(handoff_packet)

        # Step 3: Notify user
        return "Connecting you with a specialist... (typical wait: 2-3 minutes)"

        # Step 4: If no agent available, offer callback
        if queue.wait_time > 300:
            return "Our agents are busy. Would you like a callback within 1 hour?"
```

**Agent Context Template** (what the human agent sees):
```
HANDOFF SUMMARY
================
Session ID: sess_abc123
Customer: John Doe (user_123)
Escalation Reason: Low NLU confidence (2 failed turns)

CONVERSATION HISTORY
====================
Turn 1:
  User: "My order isn't arriving"
  Bot Intent: troubleshoot_issue (confidence: 0.82)
  Entities: {order_id: null}
  Bot Response: "I can help! Which order?"

Turn 2:
  User: "The one from last week"
  Bot Intent: Unresolved (confidence: 0.44) ← Problem here
  Bot Response: "I'm not sure which order. Can you share the order number?"

Turn 3:
  User: "I don't know the number"
  Bot Intent: Escalation trigger met (3rd turn, low confidence)

RECOMMENDED NEXT STEPS
======================
1. Ask customer for email or phone to look up orders
2. Review last 3 orders for unshipped status
3. If shipping delayed, offer compensation (expedited shipping)
```

## Output Template

**Chatbot Conversation Design Document**:
```markdown
# [Chatbot Name] Conversation Design

## Intent Taxonomy
[Tree of 20+ intents with descriptions, examples, required entities]

## Entity Schema
[Table of entities, extraction methods, examples]

## State Machine
[Diagram of states and transitions]

## Conversation Flows
- Happy path: [Detailed dialog]
- Error path 1: [Detailed dialog]
- Error path 2: [Detailed dialog]

## NLU Training Data
[100+ examples with labeled intents and entities]

## Escalation Triggers
[Conditions that trigger human handoff]

## Personality Guide
[Greeting style, error recovery tone, etc.]
```

## Quality Gates

1. **Intent Coverage >= 95%**: Sample 100 real user messages; bot correctly identifies intent in 95+ cases
2. **Entity Extraction F1 >= 0.85**: Precision and recall for critical entities (order_id, email, product)
3. **Error Path Success**: Every error path tested; bot recovers or escalates gracefully
4. **User Satisfaction > 4.0/5**: Survey users after escalation; verify handoff was smooth
5. **Fallback Coverage**: Every state has fallback action if user intent unrecognized
6. **Escalation SLA**: Human agent response within 30 seconds of escalation
7. **No Infinite Loops**: Dialog never gets stuck; always makes progress or escalates

## Examples

### Good Conversation: Slot-Filling with Clarification
```
User: "Book me a flight"
Bot: "I'd be happy to help! Where are you flying from?"
User: "LA to NYC"
Bot: [Extracts: origin: LA, destination: NYC] "Great! What date?"
User: "Next Friday"
Bot: [Extracts: date: 2024-01-19, return: unspecified] "Just one-way, or round trip?"
User: "Round trip, back Sunday"
Bot: [Extracts: return_date: 2024-01-21] "Got it! How many passengers?"
User: "2 of us"
Bot: [All slots filled] "Perfect! Searching for flights... [Results]"
✓ Clear slot progression, minimal back-and-forth
```

### Bad Conversation: Ambiguity Without Recovery
```
User: "Can I return it?"
Bot: "Yes, we accept returns within 30 days."
User: "I mean the other one"
Bot: "Can you clarify which order you mean?"
User: "The one I just mentioned"
Bot: "I didn't catch that. Please try again."
User: "This is frustrating"
Bot: "I understand. What can I help you with?"
❌ Bot never clarified which product; failed to resolve reference
✓ Fixed: Bot should ask "Which item? I see you have 3 recent orders."
```

## Common Mistakes

1. **No Idempotency Check / Duplicate Processing**
   - ❌ User: "Add to cart" (network lag) → User repeats: "Add to cart" → 2 items added instead of 1
   - ✓ Check idempotency: "Already adding this item to your cart" (dedup)
   - ✓ Store request ID; skip duplicate requests

2. **Over-Confirmation / Annoying Politeness**
   - ❌ High confidence: intent=add_to_cart (0.98), entities={product=iPhone (0.97), qty=1 (0.96)}
   - ❌ Bot: "Did you mean to add 1 iPhone to your cart?" (unnecessary)
   - ✓ High confidence → proceed silently: "Added iPhone to your cart!"
   - ✓ Reserve confirmation for low confidence cases

3. **Lost Context Across Turns**
   - ❌ User Turn 1: "I want the iPhone"
   - ❌ User Turn 2: "Does it come in blue?"
   - ❌ Bot: "What product are you asking about?" (forgot iPhone context)
   - ✓ Store product_context in dialog state; carry forward

4. **No Escalation Strategy / Stuck in Loop**
   - ❌ User says "Talk to someone" → Bot keeps responding with auto-replies
   - ✓ Immediate escalation: "Connecting you with an agent..."
   - ✓ Define hard escalation triggers (frustration, sensitive data)

5. **Entity Extraction Without Validation**
   - ❌ User: "I live in Calififornia"
   - ❌ Bot accepts "Calififornia" as valid state (typo)
   - ✓ Validate entity against known values: "Did you mean California?"
   - ✓ Use fuzzy matching (Levenshtein distance) for state/product names

6. **Hallucinated Capabilities**
   - ❌ User: "Can you refund me $1000?" (beyond your authority)
   - ❌ Bot: "Sure! Processing your refund now." (bot can't actually charge/refund)
   - ✓ Know capability boundaries: "I can initiate the refund, but a human must approve amounts > $500"

## Anti-Patterns

1. **Linear Waterfall Dialog Instead of Flexible State Machine**
   - ❌ Step 1 → Step 2 → Step 3 (no branching, user can't go back or skip)
   - ✓ State machine: User can jump between states, repeat, clarify
   - Impact: Rigid bot feels unnatural; users frustrated

2. **Single "Understand Everything" Intent**
   - ❌ One intent "customer_inquiry" for all 50 different user requests
   - ✓ 20+ specific intents (browse, purchase, return, support, etc.)
   - Impact: Can't route to right action; low accuracy

3. **No Distinction Between Low-Confidence Intent vs High-Confidence Entities**
   - ❌ Intent confidence 0.5 + entities confidence 0.95 → Treat both equally
   - ✓ If intent low but entities clear, ask clarification intent: "Do you want to [ACTION]?"
   - Impact: Wrong action taken even with good entity extraction

4. **Treating All Users the Same**
   - ❌ Same dialog for new users (need help) and power users (want to skip)
   - ✓ Fast-path for regulars: Skip slots if already known, offer advanced options
   - Impact: Power users give up; new users overwhelmed

5. **No Fallback for Named Entity Recognition Failures**
   - ❌ User says "John Smith" → Bot can't extract → Error
   - ✓ If extraction fails, ask for clarification: "Is your name John or Smith?"
   - ✓ Store user feedback to improve extractor
