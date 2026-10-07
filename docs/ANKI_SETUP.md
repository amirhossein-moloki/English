# AnkiConnect Configuration & Note Model Setup

## AnkiConnect Setup
1. Open Anki.
2. Go to `Tools` -> `Add-ons`.
3. Click `Get Add-ons...`, enter code `2055492153` (AnkiConnect), and restart Anki.
4. Ensure AnkiConnect is listening at `http://localhost:8765`.

## Note Model Structure: "English Vocabulary"
The application will automatically create the custom note type `English Vocabulary` if it does not already exist.

### Fields:
- `Word`: Target English word or phrase
- `Meaning`: Persian translation / meaning
- `Example`: Usage example sentence
- `PartOfSpeech`: Grammatical category (e.g., verb, noun, adjective)
- `Pronunciation`: IPA pronunciation string
- `Audio`: `[sound:filename.mp3]` reference
- `Source`: Provider source metadata (e.g., Oxford, Merriam-Webster, EdgeTTS)
- `Tags`: Space-separated tags

### Card Templates
- **Front**:
  ```html
  <div class="card front">
    <h1 class="word">{{Word}}</h1>
    <div class="audio">{{Audio}}</div>
  </div>
  ```
- **Back**:
  ```html
  <div class="card back">
    <h1 class="word">{{Word}}</h1>
    <div class="pos"><i>{{PartOfSpeech}}</i> {{Pronunciation}}</div>
    <hr>
    <div class="meaning">{{Meaning}}</div>
    <div class="example"><b>Example:</b> {{Example}}</div>
    <div class="audio">{{Audio}}</div>
    <div class="source"><small>Source: {{Source}}</small></div>
  </div>
  ```
