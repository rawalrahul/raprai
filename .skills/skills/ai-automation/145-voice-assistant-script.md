---
name: voice-assistant-script
description: "Design voice UI conversations with wake word detection, intent classification, slot-filling, confirmation patterns, SSML markup, error recovery, and multi-modal fallback. Optimize for speech constraints."
category: ai-automation
difficulty: intermediate
model_boost: "Fixes voice chatbots that fail to handle speech-specific constraints (no visual feedback, overlapping speech, accents)"
---

# Voice Assistant Script

## Purpose
This skill teaches you to design conversation flows optimized for voice interaction, accounting for speech-to-text accuracy, real-time response latency, lack of visual feedback, and hearing accessibility. You'll learn to structure conversations for wake word detection, intent classification, entity extraction, confirmation strategies, SSML markup for speech synthesis, error recovery from speech recognition failures, and graceful fallback to text/screen when needed. The output is a production-ready voice interface script with measured user satisfaction metrics.

## When to Use
- Building voice assistants (Alexa, Google Home, smart speaker apps)
- Phone-based customer service with IVR
- Voice-controlled applications
- Accessibility features requiring voice interaction
- **Do NOT use when**: Text-only interactions, real-time concurrent users on same device, or privacy-critical data collection via voice

## Instructions

### Step 1: Wake Word Detection and Activation
Detect user intent to start interaction without always listening.

**Wake Word Architecture**:
```python
class WakeWordDetector:
    """
    Detects wake words without constant cloud processing
    Optimized for: low power, privacy, low latency
    """

    def __init__(self, wake_words: list[str] = None):
        if wake_words is None:
            wake_words = ["Hey Google", "Alexa", "OK Siri"]

        # On-device small-footprint model
        from porcupine import create
        self.detector = create(
            keywords=wake_words,
            access_key="..."  # Picovoice key
        )

    def detect_in_audio_stream(self, audio_stream):
        """
        Continuously monitor audio for wake word
        Returns True when wake word detected
        """
        while True:
            # Read 512 samples (short frame)
            frame = audio_stream.read(512)

            # Detect locally (no network)
            is_activated = self.detector.process(frame)

            if is_activated:
                print("Wake word detected! Starting conversation.")
                return True

    # Alternatives:
    # - Picovoice Porcupine (local, 1-word or 3-word phrases)
    # - Siri On-Device (iOS, privacy-first)
    # - Custom TensorFlow Lite model (full control)
```

**Wake Word Best Practices**:
```yaml
wake_word_design:
  characteristics:
    - length: "2-3 words" (longer = lower false positives)
    - pronunciation: "Clear, distinct phonemes"
    - uniqueness: "Avoid common words (not 'Hey Google' vs 'Go Google')"
    - false_positive_rate: "< 1 per 1000 hours"

  examples:
    good:
      - "Hey Google" (distinct, not everyday phrase)
      - "Alexa" (single word, clear)
      - "OK Siri" (uncommon combination)

    bad:
      - "OK" (too short, too common)
      - "Google" (sounds like "Goggle")
      - "Computer" (often said in context, high false positives)

  localization:
    - "Hey Google" → "Ok Google" (Spanish: Ok Google = awkward)
    - Custom wake words per language
    - Train on diverse accents
```

**False Positive Mitigation**:
```python
class FalsePositiveFilter:
    """Filter out accidental activations"""

    def __init__(self):
        self.activation_buffer = []
        self.min_confidence = 0.85

    def filter_activation(self, detection_confidence: float,
                         audio_energy: float) -> bool:
        """
        Reduce false positives using multiple signals:
        1. Confidence score from wake word model
        2. Audio energy (speech has higher energy than background noise)
        3. Recency (multiple detections close together = real speech)
        """

        # Check confidence
        if detection_confidence < self.min_confidence:
            return False

        # Check audio energy (filter out whispers, background TV)
        if audio_energy < -40:  # dB
            return False

        # Check for consistency (require 2 detections within 500ms)
        now = time.time()
        self.activation_buffer.append(now)
        self.activation_buffer = [t for t in self.activation_buffer if now - t < 0.5]

        if len(self.activation_buffer) >= 2:
            return True

        return False
```

### Step 2: Intent Recognition from Speech
Classify what user wants to do, accounting for speech recognition errors.

**Intent Recognition Pipeline**:
```python
class VoiceIntentRecognizer:
    """
    Convert speech → intent, handling ASR (speech-to-text) errors
    """

    def __init__(self):
        self.asr_engine = GoogleSpeechToText()  # or similar
        self.intent_classifier = IntentClassifier()
        self.asr_alternatives = 3  # Request top-3 ASR hypotheses

    async def recognize_intent(self, audio_stream) -> tuple[str, float, str]:
        """
        Recognize intent from audio

        Returns:
            intent: classified intent (e.g., "set_timer")
            confidence: 0-1 confidence score
            asr_text: transcribed text for logging
        """

        # Step 1: Speech-to-text (get top 3 alternatives)
        asr_results = await self.asr_engine.recognize(
            audio_stream,
            num_alternatives=self.asr_alternatives
        )
        # Result: [
        #   {"text": "set timer for 10 minutes", "confidence": 0.95},
        #   {"text": "set timer for a time minutes", "confidence": 0.85},
        #   {"text": "set time for 10 minutes", "confidence": 0.80}
        # ]

        # Step 2: Try intent classification on all alternatives
        best_intent = None
        best_confidence = 0

        for asr_result in asr_results:
            text = asr_result["text"]
            asr_confidence = asr_result["confidence"]

            # Classify intent for this text
            intent, intent_confidence = await self.intent_classifier.classify(text)

            # Combined confidence: both ASR and intent must be confident
            combined_confidence = asr_confidence * intent_confidence

            if combined_confidence > best_confidence:
                best_confidence = combined_confidence
                best_intent = intent

        return best_intent, best_confidence, asr_results[0]["text"]

    async def recognize_with_confirmation(self, audio_stream) -> str:
        """
        Recognize intent and ask for confirmation if uncertain

        Handles common ASR errors:
        - "set a timer" vs "set alarm" (similar phonetics)
        - "10 minutes" vs "1 hour" (number confusion)
        """

        intent, confidence, asr_text = await self.recognize_intent(audio_stream)

        # Low confidence: Ask for confirmation
        if confidence < 0.70:
            # Generate clarification prompt
            self.speak("I heard: " + asr_text + ". Is that right?")
            confirmation_audio = await self.listen()

            confirmation_intent, _, _ = await self.recognize_intent(confirmation_audio)

            if confirmation_intent in ["yes", "confirm"]:
                return intent
            elif confirmation_intent in ["no", "cancel"]:
                self.speak("Let me try again. What would you like?")
                return None
            else:
                # Third attempt
                self.speak("I'm having trouble understanding. Can you try again?")
                return None

        return intent
```

**Intent Taxonomy for Voice**:
```yaml
intents:
  smart_home_control:
    turn_on_device:
      examples:
        - "Turn on the lights"
        - "Switch on bedroom lights"
        - "Activate living room lights"
      entities: [device_name, location]
      confirmation: "I'll turn on the {device_name} in {location}. Ready?"

    set_temperature:
      examples:
        - "Set temperature to 72 degrees"
        - "Make it warmer"
        - "Cool down the house"
      entities: [temperature, unit]
      confirmation: "Setting temperature to {temperature} degrees."

  timer_alarm:
    set_timer:
      examples:
        - "Set a timer for 10 minutes"
        - "Timer, 5 minutes for cooking"
      entities: [duration]
      confirmation: "Timer set for {duration}."

    set_alarm:
      examples:
        - "Alarm for 7am"
        - "Wake me up at 8 o'clock tomorrow"
      entities: [time, date]
      confirmation: "Alarm set for {time}."

  playback_control:
    play_music:
      examples:
        - "Play jazz music"
        - "Play some Beatles"
      entities: [genre, artist]
      confirmation: "Playing {artist} {genre}."

  general_qa:
    answer_question:
      examples:
        - "What's the weather?"
        - "Tell me about AI"
      entities: [query]
      no_confirmation: true  # Proceed directly
```

### Step 3: Slot-Filling with Speech-Specific Constraints
Collect information via conversational exchanges, optimizing for speech UX.

**Slot-Filling Dialog**:
```python
class VoiceSlotFiller:
    """
    Collect required slots for a task
    Optimized for: real-time response, no visual confirmation
    """

    def __init__(self, intent: str):
        self.intent = intent
        self.required_slots = self.get_required_slots(intent)
        self.filled_slots = {}

    def get_required_slots(self, intent: str) -> dict:
        """Get slots needed for intent"""
        slots_map = {
            "set_timer": {"duration": "How long?", "activity": "What for?"},
            "set_alarm": {"time": "What time?", "date": "What day?"},
            "play_music": {"artist": "Who do you want to hear?", "genre": "What style?"}
        }
        return slots_map.get(intent, {})

    async def fill_slots(self, user_utterance: str) -> bool:
        """
        Extract slots from user speech
        Returns: True if all slots filled, False if more info needed
        """

        # Step 1: Extract entities from user utterance
        entities = await self.extract_entities(user_utterance)
        self.filled_slots.update(entities)

        # Step 2: Find first unfilled required slot
        missing_slot = self.get_next_missing_slot()
        if missing_slot:
            # Prompt for missing slot
            prompt = self.required_slots[missing_slot]
            self.speak(prompt)
            return False  # Still collecting

        return True  # All slots filled

    def get_next_missing_slot(self) -> str:
        """Find first slot that hasn't been filled"""
        for slot_name in self.required_slots:
            if slot_name not in self.filled_slots:
                return slot_name
        return None

    async def extract_entities(self, utterance: str) -> dict:
        """Extract slots from speech (e.g., "10 minutes" → duration)"""
        entities = {}

        # Duration extraction
        duration_match = re.search(r'(\d+)\s*(minutes?|hours?|seconds?)', utterance)
        if duration_match:
            value, unit = duration_match.groups()
            entities["duration"] = f"{value} {unit}"

        # Time extraction (e.g., "7am", "7:30 pm")
        time_match = re.search(r'(\d{1,2})(?::(\d{2}))?\s*(am|pm)?', utterance)
        if time_match:
            entities["time"] = self.normalize_time(time_match.groups())

        # Activity extraction (heuristic)
        activities = ["cooking", "workout", "meditation", "studying"]
        for activity in activities:
            if activity in utterance.lower():
                entities["activity"] = activity

        return entities

    def normalize_time(self, match_groups) -> str:
        """Normalize time: "7 am" → "07:00", "7:30 pm" → "19:30" """
        hour, minute, period = match_groups
        hour = int(hour)
        minute = int(minute) if minute else 0

        if period and period.lower() == "pm" and hour != 12:
            hour += 12
        elif period and period.lower() == "am" and hour == 12:
            hour = 0

        return f"{hour:02d}:{minute:02d}"
```

**Multi-Turn Slot Filling Example**:
```
Bot: "What would you like to do?"
User: "Set an alarm for tomorrow morning"
  → Extracted: intent=set_alarm, date=tomorrow, time_period=morning

Bot: "What time in the morning?"
User: "7 AM"
  → Extracted: time=07:00

Bot: "Alarm set for 7 AM tomorrow."
✓ All slots filled
```

### Step 4: Confirmation Strategies for Voice
Confirm critical actions since user can't see screen.

**Confirmation Patterns**:

**Pattern 1: Simple Yes/No Confirmation**
```python
class ConfirmationHandler:
    async def simple_confirmation(self, action_summary: str) -> bool:
        """
        Ask yes/no confirmation for action

        action_summary: Human-readable description of action
        returns: True if confirmed, False if denied
        """

        self.speak(f"{action_summary}. Is that correct?")
        response_audio = await self.listen()

        intent, _, text = await self.intent_recognizer.recognize_intent(response_audio)

        if intent in ["yes", "confirm", "affirmative"]:
            return True
        elif intent in ["no", "cancel", "deny"]:
            return False
        else:
            # Didn't understand confirmation response
            self.speak("Sorry, I didn't catch that. Can you say yes or no?")
            return None
```

**Pattern 2: Disambiguation Confirmation**
```python
async def disambiguation_confirmation(self, options: list[str]) -> str:
    """
    Ask user to choose between multiple options

    options: ["Option A", "Option B", "Option C"]
    returns: Selected option
    """

    # Read options naturally
    self.speak("I found several options. Tell me the number:")
    for i, option in enumerate(options, 1):
        self.speak(f"{i}. {option}")

    response_audio = await self.listen()
    choice_intent, _, text = await self.intent_recognizer.recognize_intent(response_audio)

    # Extract number from speech
    number_match = re.search(r'\d+', text)
    if number_match:
        choice_idx = int(number_match.group(0)) - 1
        if 0 <= choice_idx < len(options):
            return options[choice_idx]

    # Fallback: ask again
    self.speak("I didn't understand that choice. Can you try again?")
    return None
```

**Pattern 3: Critical Action Dual Confirmation**
```python
async def critical_action_confirmation(self, action: str, value: str) -> bool:
    """
    For critical actions (e.g., purchase, delete), require explicit confirmation

    Pattern: Confirm action, confirm value, confirm again
    """

    # Step 1: Confirm action type
    self.speak(f"You want to {action}. Is that right?")
    if not await self.get_yes_no_response():
        return False

    # Step 2: Confirm value
    self.speak(f"You said {value}. Confirm?")
    if not await self.get_yes_no_response():
        return False

    # Step 3: Final confirmation with explicit language
    self.speak(f"This will {action} {value}. Please say 'Yes, do it' to confirm.")
    response_audio = await self.listen()
    _, _, text = await self.intent_recognizer.recognize_intent(response_audio)

    return "yes" in text.lower() and "do it" in text.lower()
```

### Step 5: SSML Markup for Natural Speech Synthesis
Use SSML to control speech prosody, pacing, and emotions.

**SSML Fundamentals**:
```python
class SSMLBuilder:
    """
    Build SSML markup for natural-sounding speech

    SSML: Speech Synthesis Markup Language (W3C standard)
    """

    def build_spoken_message(self) -> str:
        """
        Example: Build a greeting with prosody variations
        """
        ssml = """
        <speak>
            <s>
                <amazon:emotion name="excited" intensity="medium">
                    Hello! Welcome to my assistant.
                </amazon:emotion>
            </s>
            <break time="500ms"/>
            <s>
                <prosody rate="0.9">
                    I can help you with smart home controls, timers, and more.
                </prosody>
            </s>
            <break time="1000ms"/>
            <s>
                <prosody pitch="high">
                    What would you like me to do?
                </prosody>
            </s>
        </speak>
        """
        return ssml

    # Common SSML tags:
    @staticmethod
    def pause(duration_ms: int) -> str:
        """Insert pause"""
        return f'<break time="{duration_ms}ms"/>'

    @staticmethod
    def emphasis(text: str, level: str = "moderate") -> str:
        """Emphasize text: "strong", "moderate", "reduced" """
        return f'<emphasis level="{level}">{text}</emphasis>'

    @staticmethod
    def rate(text: str, rate: float = 1.0) -> str:
        """Control speech rate: 0.5-2.0 (1.0 = normal)"""
        return f'<prosody rate="{rate}">{text}</prosody>'

    @staticmethod
    def pitch(text: str, pitch: str = "high") -> str:
        """Change pitch: "x-low", "low", "medium", "high", "x-high", or percentage"""
        return f'<prosody pitch="{pitch}">{text}</prosody>'

    @staticmethod
    def volume(text: str, volume: str = "loud") -> str:
        """Change volume: "silent", "x-soft", "soft", "medium", "loud", "x-loud" """
        return f'<prosody volume="{volume}">{text}</prosody>'

    @staticmethod
    def spell_out(text: str) -> str:
        """Spell out each letter (for acronyms/codes)"""
        return f'<say-as interpret-as="characters">{text}</say-as>'

    @staticmethod
    def number_spelling(number: str) -> str:
        """Say number as spoken digits"""
        return f'<say-as interpret-as="digits">{number}</say-as>'
```

**SSML Examples**:
```python
# Example 1: Natural greeting with emotion
greeting = """
<speak>
    <amazon:emotion name="happy" intensity="medium">
        Good morning! Hope you're having a great day.
    </amazon:emotion>
</speak>
"""

# Example 2: Reading numbers naturally
phone_number_ssml = """
<speak>
    Your phone number is
    <say-as interpret-as="telephone">5551234567</say-as>
</speak>
"""
# Output: "Your phone number is five five five one two three four five six seven"

# Example 3: Confirmation with emphasis
confirmation = f"""
<speak>
    I'll set an alarm for
    <emphasis level="strong">{time}</emphasis>
    tomorrow morning.
</speak>
"""

# Example 4: Error message with concern
error_message = f"""
<speak>
    <prosody pitch="low">
        I'm having trouble connecting to the service.
    </prosody>
    <break time="500ms"/>
    Please try again in a moment.
</speak>
"""
```

### Step 6: Error Recovery from Speech Recognition Failures
Handle common ASR errors gracefully.

**Error Recovery Strategies**:
```python
class VoiceErrorHandler:
    """Handle common speech recognition and understanding errors"""

    async def handle_no_speech_detected(self, attempt: int = 1) -> str:
        """User didn't speak or background noise too high"""

        if attempt == 1:
            self.speak(
                SSML.pause(200) +
                "I didn't hear anything. Can you try again?"
            )

        elif attempt == 2:
            self.speak(
                "It's still quiet. Could you speak up?"
            )

        else:  # attempt >= 3
            self.speak(
                "I'm having trouble hearing. Let me switch to text input."
            )
            return await self.fallback_to_text()

    async def handle_poor_recognition_confidence(self, asr_text: str, confidence: float):
        """ASR confidence too low; ask for clarification"""

        if confidence < 0.5:
            # Very low confidence: ask user to repeat
            self.speak(f"Sorry, I didn't quite catch that. Can you repeat?")

        else:  # 0.5-0.7: moderate confidence
            # Clarify with specific wrong interpretation
            self.speak(f"I heard '{asr_text}'. Did I get that right?")

            confirmation_audio = await self.listen()
            confirmation_intent, _, _ = await self.intent_recognizer.recognize_intent(confirmation_audio)

            if confirmation_intent in ["yes", "confirm"]:
                return asr_text
            elif confirmation_intent in ["no", "cancel"]:
                self.speak("Let me try again. What did you say?")
                return None

    async def handle_intent_mismatch(self):
        """Recognized speech but can't classify intent"""

        self.speak(
            "I'm not sure what you mean. Can you rephrase that?"
        )
        # Retry with rephrased input

    async def handle_multiple_interpretations(self, interpretations: list[str]):
        """Multiple possible intents from same speech"""

        self.speak("I have a few options. Which one did you mean?")
        for i, interp in enumerate(interpretations, 1):
            self.speak(f"{i}. {interp}")

        # Get user choice (see disambiguation pattern)
```

**Retry Limits**:
```python
class RetryPolicy:
    """Define when to escalate from voice to fallback"""

    NO_SPEECH_RETRIES = 3  # After 3 times hearing nothing, offer text
    LOW_CONFIDENCE_RETRIES = 2  # After 2 low-confidence attempts, clarify
    UNRECOGNIZED_INTENT_RETRIES = 2  # After 2 failures to classify, escalate

    async def should_fallback_to_text(self, attempt: int, error_type: str) -> bool:
        """Decide if we should offer text input fallback"""
        if error_type == "no_speech" and attempt >= self.NO_SPEECH_RETRIES:
            return True
        if error_type == "low_confidence" and attempt >= self.LOW_CONFIDENCE_RETRIES:
            return True
        if error_type == "unrecognized_intent" and attempt >= self.UNRECOGNIZED_INTENT_RETRIES:
            return True
        return False
```

### Step 7: Multi-Modal Fallback (Text/Screen)
Gracefully degrade to text/visual when voice fails.

**Fallback Strategy**:
```python
class MultiModalFallback:
    """Seamlessly switch between voice, text, and visual"""

    async def fallback_to_text_input(self):
        """Switch to text input"""
        self.speak("Switching to text mode. You can type your request.")
        self.show_text_input_field()

        # Wait for text input
        text_input = await self.get_text_input()
        return text_input

    async def fallback_to_screen(self, content: dict):
        """Display options visually instead of speaking"""
        # content = {"options": [...], "images": [...], "links": [...]}

        self.speak("Let me show you some options on your screen.")
        self.display_options_on_screen(content)

        # User can tap/click to select
        selection = await self.get_screen_input()
        return selection

    async def handle_complex_query_with_fallback(self, query: str):
        """For complex queries, use text + visual"""

        # Try voice-only first
        response = await self.process_voice_only(query)

        if not response or response["confidence"] < 0.6:
            # Fallback: Show visual options
            self.speak("Let me show you some options.")
            await self.fallback_to_screen(response)

    async def offer_screen_when_needed(self):
        """Proactively offer screen for complex info"""
        # If response is long, offer to show on screen instead of reading
        response_length = len(self.current_response)

        if response_length > 500:  # More than ~30 seconds of speech
            self.speak("This is a lot of information. Would you like me to show it on your screen?")
            user_choice = await self.get_yes_no_response()

            if user_choice:
                await self.fallback_to_screen({"text": self.current_response})
```

## Output Template

**Voice Assistant Dialog Script**:
```markdown
# [Assistant Name] Voice Script

## Overview
[Purpose, device platform, target user]

## Intent Taxonomy
[Tree of intents with examples and entities]

## Sample Dialogs
[Complete conversations for key scenarios]

## SSML Configuration
[Prosody settings, personality guide]

## Error Handling
[Recovery flows for common errors]

## Accessibility
[Keyboard shortcuts, screen reader support]
```

## Quality Gates

1. **Intent Recognition Accuracy >= 90%**: Correctly classify user intent
2. **Entity Extraction F1 >= 0.85**: Extract required slots accurately
3. **Confirmation Success Rate >= 95%**: User confirms action correctly
4. **ASR Error Recovery >= 80%**: Recover without escalation
5. **End-to-End Latency < 2s**: Wake word to first response
6. **User Satisfaction > 4.5/5**: Post-interaction surveys
7. **Accessibility Compliance**: WCAG 2.1 AA for screen readers

## Examples

### Good Voice Dialog: Set Timer
```
User: "Hey Google"
Bot: [Listening state]
User: "Set a timer for 10 minutes for cooking"
Bot: [SSML with confirmation]
  "Setting a <emphasis>10 minute</emphasis> timer for cooking.
   Ready?"
User: "Yes"
Bot: [SSML with positive prosody]
  "Timer set! I'll let you know when time's up."
✓ 2.1s total latency, 0 clarifications
```

## Common Mistakes

1. **No Confirmation for Critical Actions**
   - ❌ User says "delete" → Bot deletes immediately
   - ✓ Require explicit "Yes, delete it" confirmation

2. **Ignoring Background Noise**
   - ❌ "OK Google" triggers from TV, radio
   - ✓ Use confidence filtering + recency buffer

3. **Reading Entire Form Back to User**
   - ❌ "Your name is John, phone is 555-1234, email is..." (30 sec)
   - ✓ Confirm only critical fields; show rest on screen

4. **No Fallback to Text**
   - ❌ User can't use device because background noise too high
   - ✓ After 3 retries, offer text input

## Anti-Patterns

1. **Expecting Perfect ASR**
   - ❌ No confirmation needed, ASR is 100% accurate
   - ✓ Always assume some errors; build confirmation into dialog

2. **Too Many Back-and-Forth Clarifications**
   - ❌ "Did you mean X?" (repeat 5+ times) → User abandons
   - ✓ Clarify once or twice; escalate or use visual fallback

3. **Ignoring SSML for Emotion/Prosody**
   - ❌ Robotic voice reads everything at same pace
   - ✓ Use SSML for emphasis, pauses, emotion in key moments
